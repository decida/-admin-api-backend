"""
Sistema de rotas dinâmicas para API Resources.

Este módulo gerencia a criação e remoção dinâmica de endpoints
baseados nos API Resources ativos no banco de dados.
"""

import base64
import logging
from typing import Any, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status, Body
from pydantic import BaseModel, Field, create_model, ConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.api_resource import ApiResource
from app.models.business_object import BusinessObject
from app.models.database import Database

logger = logging.getLogger(__name__)

# Router global para rotas dinâmicas
dynamic_router = APIRouter(tags=["smart-resources"])

# Cache de rotas registradas (path -> resource_id)
_registered_routes: dict[str, str] = {}


def create_request_schema(business_object_params: list[dict]) -> type[BaseModel]:
    """
    Cria dinamicamente um schema Pydantic baseado nos parâmetros do business object.

    O schema segue a estrutura esperada pelo SDK admin_api_lite:
    {
        "resource_id": "uuid",       # UUID4 do API Resource (obrigatório, validado)
        "connectionId": "string",    # ou "connection_id" - ID da conexão (obrigatório, string livre)
        "param1": "value1",          # parâmetros do business object
        "param2": "value2",
        ...
    }

    Args:
        business_object_params: Lista de definições de parâmetros do business object

    Returns:
        Classe Pydantic BaseModel gerada dinamicamente

    Example:
        >>> params = [
        ...     {"name": "cpf", "type": "string", "required": False, "defaultValue": None},
        ...     {"name": "idade", "type": "number", "required": True, "defaultValue": 18}
        ... ]
        >>> Schema = create_request_schema(params)
        >>> request = Schema(connectionId="uuid", cpf="12345678900", idade=25)
    """
    # Campos do schema
    fields = {}

    # Campo obrigatório: resource_id (UUID4)
    fields["resource_id"] = (UUID, Field(..., description="API Resource UUID (required)"))

    # Campo obrigatório: connectionId ou connection_id
    # Aceita ambos os formatos (camelCase e snake_case) via alias
    # Tipo: string (não validado como UUID, aceita qualquer string)
    fields["connectionId"] = (str, Field(..., alias="connection_id", description="Database connection ID (required)"))

    # Adicionar parâmetros dinâmicos baseados em business_object_params
    for param in business_object_params:
        param_name = param.get("name")
        param_type = param.get("type", "string")
        required = param.get("required", False)
        default_value = param.get("defaultValue")

        # Mapear tipo do parâmetro para tipo Python/Pydantic
        if param_type == "number":
            python_type = Union[float, int]
        elif param_type == "date":
            python_type = str  # Aceitar como string, validar formato depois se necessário
        else:  # string
            python_type = str

        # Determinar se é opcional ou obrigatório
        if required and default_value is None:
            # Campo obrigatório sem default
            fields[param_name] = (python_type, Field(..., description=f"Parameter: {param_name}"))
        else:
            # Campo opcional ou com default
            fields[param_name] = (Optional[python_type], Field(default=default_value, description=f"Parameter: {param_name}"))

    # Criar modelo dinâmico
    # Em Pydantic v2, usamos ConfigDict em vez de __config__
    DynamicRequestModel = create_model(
        "DynamicRequestModel",
        __config__=ConfigDict(populate_by_name=True),  # Permite usar aliases
        **fields
    )

    return DynamicRequestModel


def replace_colon_parameters(
    sql_command: str,
    parameters: dict[str, Any],
    business_object_params: list[dict]
) -> str:
    """
    Replace placeholders in SQL command with actual values using :parameter format.
    Uses the params definition from the business object to determine types and defaults.

    Args:
        sql_command: SQL command with placeholders in format :parameter_name
        parameters: Dictionary with parameter values (from request)
        business_object_params: List of param definitions from business object

    Returns:
        SQL command with replaced values (with proper typing and defaults)
    """
    from app.utils.parameter_validation import extract_sql_parameters

    # Extract parameters from SQL
    sql_params = extract_sql_parameters(sql_command)

    # Convert params list to dict for easier lookup
    param_definitions = {p['name']: p for p in business_object_params}

    # Replace parameters in SQL
    result_sql = sql_command
    for param_name in sql_params:
        placeholder = f":{param_name}"

        # Get parameter definition
        param_def = param_definitions.get(param_name)

        # Determine the value to use
        if param_name in parameters and parameters[param_name] is not None and parameters[param_name] != "":
            # Use provided value
            value = parameters[param_name]

            # Type conversion based on param definition
            if param_def:
                if param_def.get('type') == "number":
                    # No quotes for numbers
                    try:
                        # Validate it's a number
                        float(value)
                        result_sql = result_sql.replace(placeholder, str(value))
                    except (ValueError, TypeError):
                        # If not a valid number, treat as NULL
                        result_sql = result_sql.replace(placeholder, "NULL")
                elif param_def.get('type') == "date":
                    # Quotes for dates
                    safe_value = str(value).replace("'", "''")
                    result_sql = result_sql.replace(placeholder, f"'{safe_value}'")
                else:  # string
                    # Escape single quotes and add quotes
                    safe_value = str(value).replace("'", "''")
                    result_sql = result_sql.replace(placeholder, f"'{safe_value}'")
            else:
                # No definition, treat as string
                safe_value = str(value).replace("'", "''")
                result_sql = result_sql.replace(placeholder, f"'{safe_value}'")

        elif param_def and param_def.get('defaultValue') is not None:
            # Use default value from definition
            default_val = param_def['defaultValue']

            if param_def.get('type') == "number":
                result_sql = result_sql.replace(placeholder, str(default_val))
            elif param_def.get('type') == "date":
                safe_value = str(default_val).replace("'", "''")
                result_sql = result_sql.replace(placeholder, f"'{safe_value}'")
            else:  # string
                safe_value = str(default_val).replace("'", "''")
                result_sql = result_sql.replace(placeholder, f"'{safe_value}'")

        else:
            # No value provided and no default - use NULL
            result_sql = result_sql.replace(placeholder, "NULL")

    return result_sql


async def execute_dynamic_endpoint_logic(
    api_resource: ApiResource,
    connection_id: str,
    parameters: dict[str, Any],
    db: Session
) -> dict:
    """
    Execute a dynamic API resource endpoint logic (core execution).

    This function handles two execution modes:
    1. Legacy mode (single business object): Uses business_object_id
    2. Chain mode (multiple business objects): Uses execution_chain

    Args:
        api_resource: API resource object
        connection_id: Database connection ID (string)
        parameters: Request parameters (without connectionId)
        db: Database session

    Returns:
        Dict with execution results

    Raises:
        HTTPException: If execution fails
    """
    # 1. Fetch Business Object
    business_object = db.query(BusinessObject).filter(
        BusinessObject.id == api_resource.business_object_id
    ).first()
    if not business_object:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Associated Business Object not found"
        )

    # 2. Check if execution_chain exists and has steps
    # - If execution_chain exists: Use chain execution mode (new feature)
    # - If execution_chain is None/empty: Use legacy single business object mode
    if api_resource.execution_chain and len(api_resource.execution_chain) > 0:
        # Chain mode: execute chain
        from app.core.chain_executor import execute_chain, ChainExecutionException
        from app.schemas.api_resource import ExecutionChainStep

        try:
            # Convert execution_chain to ExecutionChainStep objects
            chain_steps = [ExecutionChainStep(**step) for step in api_resource.execution_chain]

            # Execute chain
            result = execute_chain(
                chain=chain_steps,
                request_payload=parameters,
                connection_id=connection_id,
                db=db
            )

            return result

        except ChainExecutionException as e:
            logger.error(f"Chain execution failed: {e.message}")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "step": e.step,
                    "businessObjectName": e.business_object_name,
                    "details": e.details
                }
            }
        except Exception as e:
            logger.error(f"Unexpected error in chain execution: {str(e)}")
            return {
                "success": False,
                "error": {
                    "message": f"Unexpected error: {str(e)}",
                    "details": str(e)
                }
            }

    # Legacy mode: execute single business object

    # 3. Decode SQL command
    try:
        decoded_sql = base64.b64decode(business_object.sql_command).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to decode SQL command: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decode SQL command: {str(e)}"
        )

    # 4. Replace parameters
    try:
        final_sql = replace_colon_parameters(
            decoded_sql,
            parameters,
            api_resource.business_object_params
        )
    except Exception as e:
        logger.error(f"Failed to replace parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process parameters: {str(e)}"
        )

    # 5. Fetch connection
    try:
        connection = db.query(Database).filter(Database.id == connection_id).first()
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection with id {connection_id} not found"
            )

        if connection.status.value != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection {connection.name} is not active"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch connection: {str(e)}"
        )

    # 6. Execute SQL
    try:
        engine = create_engine(
            connection.connection_string,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
        )

        with engine.connect() as conn:
            result = conn.execute(text(final_sql))

            # For SELECT queries, fetch results
            if business_object.command_type.value == "select":
                rows = []
                for row in result:
                    # Convert row to dictionary
                    row_dict = dict(row._mapping)
                    # Convert non-serializable types to strings
                    for key, value in row_dict.items():
                        if not isinstance(value, (str, int, float, bool, type(None))):
                            row_dict[key] = str(value)
                    rows.append(row_dict)

                return {
                    "success": True,
                    "rows": rows,
                    "rowCount": len(rows)
                }
            else:
                # For INSERT/UPDATE/DELETE, commit and return affected rows
                conn.commit()
                return {
                    "success": True,
                    "rows": [],
                    "rowCount": result.rowcount
                }

    except Exception as e:
        error_message = str(e)
        logger.error(f"SQL execution failed: {error_message}")

        # Clean up common error messages
        if "authentication" in error_message.lower() or "password" in error_message.lower():
            error_message = "Authentication failed - check connection credentials"
        elif "timeout" in error_message.lower():
            error_message = "Query timeout - operation took too long"
        elif "syntax" in error_message.lower():
            error_message = f"SQL syntax error: {error_message}"

        return {
            "success": False,
            "error": error_message
        }


async def execute_dynamic_endpoint(
    request: Request,
    resource_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    Execute a dynamic API resource endpoint.

    This function handles two execution modes:
    1. Legacy mode (single business object): Uses business_object_id
    2. Chain mode (multiple business objects): Uses execution_chain

    Flow:
    1. Fetches the API resource by ID
    2. Validates it's active
    3. Checks if execution_chain exists
    4. If chain exists: execute_chain()
    5. If no chain: execute single business object (legacy mode)

    Args:
        request: FastAPI request object
        resource_id: UUID of the API resource
        db: Database session

    Returns:
        Dict with execution results

    Raises:
        HTTPException: If resource not found, inactive, or execution fails
    """
    # 1. Fetch API resource
    api_resource = db.query(ApiResource).filter(ApiResource.id == resource_id).first()
    if not api_resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API resource not found"
        )

    # 2. Validate it's active
    if not api_resource.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API resource is not active"
        )

    # 3. Fetch Business Object
    business_object = db.query(BusinessObject).filter(
        BusinessObject.id == api_resource.business_object_id
    ).first()
    if not business_object:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Associated Business Object not found"
        )

    # 4. Get request body
    try:
        body = await request.json()
    except Exception:
        body = {}

    # Extract connection_id and parameters
    print(body)
    connection_id = body.get('connection_id') or body.get('connectionId')
    if not connection_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="connection_id is required in request body"
        )

    # Get parameters (everything except connection_id)
    parameters = {k: v for k, v in body.items() if k not in ['connection_id', 'connectionId']}

    # COMPATIBILITY: Check if execution_chain exists and has steps
    # - If execution_chain exists: Use chain execution mode (new feature)
    # - If execution_chain is None/empty: Use legacy single business object mode
    # This ensures backward compatibility with existing resources created before chain feature
    if api_resource.execution_chain and len(api_resource.execution_chain) > 0:
        # Chain mode: execute chain
        from app.core.chain_executor import execute_chain, ChainExecutionException
        from app.schemas.api_resource import ExecutionChainStep

        try:
            # Convert execution_chain to ExecutionChainStep objects
            chain_steps = [ExecutionChainStep(**step) for step in api_resource.execution_chain]

            # Execute chain
            result = execute_chain(
                chain=chain_steps,
                request_payload=parameters,
                connection_id=connection_id,
                db=db
            )

            return result

        except ChainExecutionException as e:
            logger.error(f"Chain execution failed: {e.message}")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "step": e.step,
                    "businessObjectName": e.business_object_name,
                    "details": e.details
                }
            }
        except Exception as e:
            logger.error(f"Unexpected error in chain execution: {str(e)}")
            return {
                "success": False,
                "error": {
                    "message": f"Unexpected error: {str(e)}",
                    "details": str(e)
                }
            }

    # Legacy mode: execute single business object

    # 5. Decode SQL command
    try:
        decoded_sql = base64.b64decode(business_object.sql_command).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to decode SQL command: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decode SQL command: {str(e)}"
        )

    # 6. Replace parameters
    try:
        final_sql = replace_colon_parameters(
            decoded_sql,
            parameters,
            api_resource.business_object_params
        )
    except Exception as e:
        logger.error(f"Failed to replace parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process parameters: {str(e)}"
        )

    # 7. Fetch connection
    try:
        connection = db.query(Database).filter(Database.id == connection_id).first()
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection with id {connection_id} not found"
            )

        if connection.status.value != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection {connection.name} is not active"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch connection: {str(e)}"
        )

    # 8. Execute SQL
    try:
        engine = create_engine(
            connection.connection_string,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
        )

        with engine.connect() as conn:
            result = conn.execute(text(final_sql))

            # For SELECT queries, fetch results
            if business_object.command_type.value == "select":
                rows = []
                for row in result:
                    # Convert row to dictionary
                    row_dict = dict(row._mapping)
                    # Convert non-serializable types to strings
                    for key, value in row_dict.items():
                        if not isinstance(value, (str, int, float, bool, type(None))):
                            row_dict[key] = str(value)
                    rows.append(row_dict)

                return {
                    "success": True,
                    "rows": rows,
                    "rowCount": len(rows)
                }
            else:
                # For INSERT/UPDATE/DELETE, commit and return affected rows
                conn.commit()
                return {
                    "success": True,
                    "rows": [],
                    "rowCount": result.rowcount
                }

    except Exception as e:
        error_message = str(e)
        logger.error(f"SQL execution failed: {error_message}")

        # Clean up common error messages
        if "authentication" in error_message.lower() or "password" in error_message.lower():
            error_message = "Authentication failed - check connection credentials"
        elif "timeout" in error_message.lower():
            error_message = "Query timeout - operation took too long"
        elif "syntax" in error_message.lower():
            error_message = f"SQL syntax error: {error_message}"

        return {
            "success": False,
            "error": error_message
        }


def refresh_dynamic_routes(db: Session) -> None:
    """
    Refresh dynamic routes based on active API resources.

    This function:
    1. Clears all existing routes from the dynamic router
    2. Queries all active API resources
    3. Registers a new route for each active resource

    Note: This is called automatically when API resources are created/updated/deleted.
    It can also be called manually during application startup.

    Args:
        db: Database session
    """
    global _registered_routes

    # Clear existing routes
    dynamic_router.routes.clear()
    _registered_routes.clear()

    # Get all active API resources
    api_resources = db.query(ApiResource).filter(ApiResource.is_active == True).all()

    logger.info(f"Refreshing dynamic routes: found {len(api_resources)} active resources")

    # Register routes
    for resource in api_resources:
        try:
            # Criar schema Pydantic dinâmico baseado nos parâmetros
            RequestSchema = create_request_schema(resource.business_object_params)

            # Create endpoint function factory para evitar problema de closure
            def make_endpoint(resource_id: str, request_schema: type[BaseModel]):
                """Factory para criar endpoint com closure correta."""
                async def endpoint(
                    body: request_schema = Body(...),  # type: ignore
                    db: Session = Depends(get_db)
                ):
                    # Converter body Pydantic para dict
                    body_dict = body.model_dump(by_alias=True, exclude_none=False)

                    # Extrair resource_id do body
                    body_resource_id = body_dict.get('resource_id')
                    if not body_resource_id:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="resource_id is required in request body"
                        )

                    # Validar que o resource_id do body corresponde ao resource_id da rota
                    # Converter para string para comparação (pode vir como UUID object)
                    if str(body_resource_id) != str(resource_id):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"resource_id mismatch: expected {resource_id}, got {body_resource_id}"
                        )

                    # Extrair connectionId (pode vir como connectionId ou connection_id)
                    connection_id = body_dict.get('connectionId') or body_dict.get('connection_id')
                    if not connection_id:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="connectionId is required in request body"
                        )

                    # Extrair parâmetros (tudo exceto connectionId/connection_id/resource_id)
                    parameters = {
                        k: v for k, v in body_dict.items()
                        if k not in ['connectionId', 'connection_id', 'resource_id'] and v is not None
                    }

                    # Buscar API resource
                    api_resource = db.query(ApiResource).filter(ApiResource.id == resource_id).first()
                    if not api_resource:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="API resource not found"
                        )

                    if not api_resource.is_active:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="API resource is not active"
                        )

                    # Executar via execute_dynamic_endpoint_logic
                    return await execute_dynamic_endpoint_logic(
                        api_resource=api_resource,
                        connection_id=connection_id,
                        parameters=parameters,
                        db=db
                    )

                return endpoint

            # Criar endpoint com o schema correto
            endpoint_func = make_endpoint(str(resource.id), RequestSchema)

            # Register the route
            dynamic_router.add_api_route(
                path=resource.path,
                endpoint=endpoint_func,
                methods=[resource.method],
                summary=resource.description or f"Execute {resource.business_object_name}",
                response_model=None,
                status_code=status.HTTP_200_OK
            )

            _registered_routes[resource.path] = str(resource.id)
            logger.info(f"Registered dynamic route: {resource.method} {resource.path}")

        except Exception as e:
            logger.error(f"Failed to register route {resource.path}: {e}")


def get_registered_routes() -> dict[str, str]:
    """
    Get currently registered dynamic routes.

    Returns:
        Dict mapping path to resource_id
    """
    return _registered_routes.copy()
