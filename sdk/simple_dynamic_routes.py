"""
Simple Dynamic Routes - Sistema de rotas dinâmicas minimalista

Versão simplificada que usa AdminAPILite para buscar metadados
e criar rotas dinamicamente.

USO:
    from admin_api_lite import AdminAPILite
    from simple_dynamic_routes import setup_dynamic_routes, dynamic_router

    # No startup do FastAPI
    admin_client = AdminAPILite(base_url="http://admin-api:8000")
    setup_dynamic_routes(admin_client)

    # Incluir router no app
    app.include_router(dynamic_router)
"""

import base64
import logging
from typing import Any
from fastapi import APIRouter, HTTPException, Request, status

logger = logging.getLogger(__name__)

# Router global para rotas dinâmicas
dynamic_router = APIRouter(tags=["dynamic-routes"])

# Admin API client (configurado via setup)
_admin_client = None


def setup_dynamic_routes(admin_client):
    """
    Configura rotas dinâmicas usando AdminAPILite.

    Args:
        admin_client: Instância do AdminAPILite configurada

    Example:
        >>> from admin_api_lite import AdminAPILite
        >>> from simple_dynamic_routes import setup_dynamic_routes, dynamic_router
        >>>
        >>> client = AdminAPILite(base_url="http://localhost:8000")
        >>> setup_dynamic_routes(client)
        >>>
        >>> # No FastAPI app
        >>> app.include_router(dynamic_router)
    """
    global _admin_client
    _admin_client = admin_client

    logger.info("Fetching API resources from Admin API...")

    try:
        # Buscar recursos ativos
        resources = admin_client.list_api_resources(active_only=True)

        logger.info(f"Found {len(resources)} active API resources")

        # Limpar rotas existentes
        dynamic_router.routes.clear()

        # Registrar cada resource como rota
        for resource in resources:
            try:
                register_route(resource)
                logger.info(f"✓ Registered: {resource['method']} {resource['path']}")
            except Exception as e:
                logger.error(f"✗ Failed to register {resource.get('path')}: {e}")

        logger.info(f"Dynamic routes setup complete: {len(dynamic_router.routes)} routes registered")

    except Exception as e:
        logger.error(f"Failed to setup dynamic routes: {e}")
        raise


def register_route(resource: dict):
    """
    Registra uma rota dinâmica no router.

    Args:
        resource: Dicionário com metadados do API Resource
    """
    path = resource["path"]
    method = resource["method"]
    resource_id = resource["id"]

    # Criar função de endpoint
    async def endpoint(request: Request):
        return await execute_resource(resource_id, request)

    # Registrar rota
    dynamic_router.add_api_route(
        path=path,
        endpoint=endpoint,
        methods=[method],
        summary=resource.get("description") or f"Execute {resource.get('businessObjectName')}",
        status_code=status.HTTP_200_OK
    )


async def execute_resource(resource_id: str, request: Request) -> dict:
    """
    Executa um API Resource.

    Args:
        resource_id: UUID do resource
        request: Request FastAPI

    Returns:
        Resultado da execução
    """
    if _admin_client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin client not configured"
        )

    # Obter body do request
    try:
        body = await request.json()
    except Exception:
        body = {}

    # Extrair connection_id
    connection_id = body.get("connectionId") or body.get("connection_id")
    if not connection_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="connectionId is required"
        )

    # Buscar metadata do resource
    try:
        resource = _admin_client._get_resource(resource_id)
    except Exception as e:
        logger.error(f"Failed to fetch resource: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource not found: {str(e)}"
        )

    # Buscar database connection
    try:
        database = _admin_client.get_database(connection_id)
    except Exception as e:
        logger.error(f"Failed to fetch database: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database not found: {str(e)}"
        )

    # Validar status da conexão
    if database.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database connection is not active"
        )

    # Decode SQL do business object
    try:
        # O business object está embedado no resource (businessObject field)
        # Ou podemos buscar via outro endpoint - vamos assumir que está no resource
        sql_command_b64 = resource.get("businessObject", {}).get("sqlCommand")
        if not sql_command_b64:
            raise Exception("SQL command not found in resource")

        sql_command = base64.b64decode(sql_command_b64).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to decode SQL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decode SQL: {str(e)}"
        )

    # Substituir parâmetros no SQL
    parameters = {k: v for k, v in body.items() if k not in ["connectionId", "connection_id"]}
    business_object_params = resource.get("businessObjectParams", [])

    try:
        final_sql = replace_sql_parameters(sql_command, parameters, business_object_params)
    except Exception as e:
        logger.error(f"Failed to replace parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process parameters: {str(e)}"
        )

    # Executar SQL
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(
            database["connectionString"],
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0
        )

        with engine.connect() as conn:
            result = conn.execute(text(final_sql))

            # Business object command type
            command_type = resource.get("businessObject", {}).get("commandType", "select")

            if command_type == "select":
                rows = []
                for row in result:
                    row_dict = dict(row._mapping)
                    # Convert non-serializable types
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
                conn.commit()
                return {
                    "success": True,
                    "rows": [],
                    "rowCount": result.rowcount
                }

    except Exception as e:
        error_message = str(e)
        logger.error(f"SQL execution failed: {error_message}")

        return {
            "success": False,
            "error": error_message
        }


def replace_sql_parameters(
    sql_command: str,
    parameters: dict[str, Any],
    business_object_params: list[dict]
) -> str:
    """
    Substitui parâmetros no SQL command (:param format).

    Args:
        sql_command: SQL com placeholders :paramName
        parameters: Valores dos parâmetros
        business_object_params: Definições dos parâmetros

    Returns:
        SQL com parâmetros substituídos
    """
    import re

    # Extrair parâmetros do SQL
    pattern = r':([a-zA-Z_][a-zA-Z0-9_]*)'
    param_names = set(re.findall(pattern, sql_command))

    # Converter params para dict
    param_defs = {p["name"]: p for p in business_object_params}

    # Substituir cada parâmetro
    result_sql = sql_command

    for param_name in param_names:
        placeholder = f":{param_name}"
        param_def = param_defs.get(param_name, {})

        # Obter valor
        if param_name in parameters and parameters[param_name] is not None:
            value = parameters[param_name]
            param_type = param_def.get("type", "string")

            # Formatar valor baseado no tipo
            if param_type == "number":
                try:
                    float(value)
                    result_sql = result_sql.replace(placeholder, str(value))
                except (ValueError, TypeError):
                    result_sql = result_sql.replace(placeholder, "NULL")
            else:
                # String ou date - adicionar quotes e escapar
                safe_value = str(value).replace("'", "''")
                result_sql = result_sql.replace(placeholder, f"'{safe_value}'")

        elif param_def.get("defaultValue") is not None:
            # Usar default
            default_val = param_def["defaultValue"]
            param_type = param_def.get("type", "string")

            if param_type == "number":
                result_sql = result_sql.replace(placeholder, str(default_val))
            else:
                safe_value = str(default_val).replace("'", "''")
                result_sql = result_sql.replace(placeholder, f"'{safe_value}'")
        else:
            # NULL
            result_sql = result_sql.replace(placeholder, "NULL")

    return result_sql


def refresh_routes(admin_client=None):
    """
    Refresh dynamic routes (re-fetch from Admin API).

    Args:
        admin_client: Optional new AdminAPILite instance. If None, uses existing.
    """
    client = admin_client or _admin_client
    if not client:
        raise Exception("Admin client not configured")

    setup_dynamic_routes(client)
