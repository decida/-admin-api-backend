import base64
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.business_object import BusinessObject
from app.models.database import Database
from app.schemas.business_object import (
    BusinessObjectCreate,
    BusinessObjectResponse,
    BusinessObjectUpdate,
    BusinessObjectTestRequest,
    BusinessObjectTestResponse,
    ExecuteSqlRequest,
)
from app.utils.parameter_validation import validate_parameters, convert_to_dict

router = APIRouter()


def extract_parameters(sql_command: str) -> set[str]:
    """
    Extract parameter names from SQL command.
    Parameters are in the format {{parameter_name}}.
    Returns a set of unique parameter names.
    """
    pattern = r'\{\{(\w+)\}\}'
    matches = re.findall(pattern, sql_command)
    return set(matches)


def replace_parameters(sql_command: str, parameters: dict[str, str]) -> str:
    """
    Replace placeholders in SQL command with actual values.
    All parameters are optional - missing parameters are replaced with NULL.

    Args:
        sql_command: SQL command with placeholders in format {{parameter_name}}
        parameters: Dictionary with parameter values (optional)

    Returns:
        SQL command with replaced values (missing params replaced with NULL)
    """
    # Extract all parameters from SQL
    all_params = extract_parameters(sql_command)

    # Replace parameters in SQL
    result_sql = sql_command
    for param_name in all_params:
        placeholder = f"{{{{{param_name}}}}}"

        # Check if parameter is provided and has a value
        if param_name in parameters and parameters[param_name]:
            # Escape single quotes in parameter value to prevent SQL injection
            safe_value = parameters[param_name].replace("'", "''")
            result_sql = result_sql.replace(placeholder, f"'{safe_value}'")
        else:
            # Replace with NULL if not provided or empty
            result_sql = result_sql.replace(placeholder, "NULL")

    return result_sql


def replace_colon_parameters(sql_command: str, parameters: dict[str, str], business_object: BusinessObject) -> str:
    """
    Replace placeholders in SQL command with actual values using :parameter format.
    Uses the params definition from the business object to determine types and defaults.

    Args:
        sql_command: SQL command with placeholders in format :parameter_name
        parameters: Dictionary with parameter values (from request)
        business_object: BusinessObject with params definitions

    Returns:
        SQL command with replaced values (with proper typing and defaults)
    """
    from app.utils.parameter_validation import extract_sql_parameters, convert_from_dict

    # Extract parameters from SQL
    sql_params = extract_sql_parameters(sql_command)

    # Convert params from dict to SqlParameter objects
    param_definitions = {p.name: p for p in convert_from_dict(business_object.params)}

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
                if param_def.type == "number":
                    # No quotes for numbers
                    try:
                        # Validate it's a number
                        float(value)
                        result_sql = result_sql.replace(placeholder, str(value))
                    except ValueError:
                        # If not a valid number, treat as NULL
                        result_sql = result_sql.replace(placeholder, "NULL")
                elif param_def.type == "date":
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

        elif param_def and param_def.defaultValue is not None:
            # Use default value from definition
            default_val = param_def.defaultValue

            if param_def.type == "number":
                result_sql = result_sql.replace(placeholder, str(default_val))
            elif param_def.type == "date":
                safe_value = str(default_val).replace("'", "''")
                result_sql = result_sql.replace(placeholder, f"'{safe_value}'")
            else:  # string
                safe_value = str(default_val).replace("'", "''")
                result_sql = result_sql.replace(placeholder, f"'{safe_value}'")

        else:
            # No value provided and no default - use NULL
            result_sql = result_sql.replace(placeholder, "NULL")

    return result_sql


@router.get("/", response_model=list[BusinessObjectResponse])
def get_business_objects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> list[BusinessObjectResponse]:
    """
    Retrieve all business objects.
    SQL commands are returned in BASE64.
    """
    business_objects = db.query(BusinessObject).offset(skip).limit(limit).all()
    return business_objects


@router.get("/{id}", response_model=BusinessObjectResponse)
def get_business_object(
    id: UUID,
    db: Session = Depends(get_db)
) -> BusinessObjectResponse:
    """
    Get business object by ID.
    SQL command is returned in BASE64.
    """
    business_object = db.query(BusinessObject).filter(BusinessObject.id == id).first()
    if not business_object:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business object with id {id} not found",
        )
    return business_object


@router.post("/", response_model=BusinessObjectResponse, status_code=status.HTTP_201_CREATED)
def create_business_object(
    business_object_in: BusinessObjectCreate,
    db: Session = Depends(get_db)
) -> BusinessObjectResponse:
    """
    Create new business object.
    SQL command must be provided in BASE64.
    Command type cannot be changed after creation.
    Parameters are validated against the SQL command.
    """
    # Validate parameters
    is_valid, errors = validate_parameters(business_object_in.sql_command, business_object_in.params)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Parameter validation failed",
                "details": errors
            }
        )

    # Check if name already exists
    existing = db.query(BusinessObject).filter(BusinessObject.name == business_object_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Business object with name '{business_object_in.name}' already exists",
        )

    # Convert params to dict for storage
    data = business_object_in.model_dump()
    data['params'] = convert_to_dict(business_object_in.params)

    # Create business object
    business_object = BusinessObject(**data)
    db.add(business_object)
    db.commit()
    db.refresh(business_object)

    return business_object


@router.patch("/{id}", response_model=BusinessObjectResponse)
def update_business_object(
    id: UUID,
    business_object_in: BusinessObjectUpdate,
    db: Session = Depends(get_db)
) -> BusinessObjectResponse:
    """
    Update business object.
    Command type cannot be changed after creation (excluded from update schema).
    SQL command must be in BASE64 if provided.
    Parameters are validated against the SQL command if either sql_command or params are updated.
    """
    business_object = db.query(BusinessObject).filter(BusinessObject.id == id).first()
    if not business_object:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business object with id {id} not found",
        )

    # Check if name already exists (if name is being updated)
    if business_object_in.name and business_object_in.name != business_object.name:
        existing = db.query(BusinessObject).filter(BusinessObject.name == business_object_in.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Business object with name '{business_object_in.name}' already exists",
            )

    # Validate parameters if sql_command or params are being updated
    if business_object_in.sql_command is not None or business_object_in.params is not None:
        # Use updated sql_command if provided, otherwise use existing
        sql_to_validate = business_object_in.sql_command if business_object_in.sql_command is not None else business_object.sql_command
        # Use updated params if provided, otherwise use existing (convert from dict)
        from app.utils.parameter_validation import convert_from_dict
        params_to_validate = business_object_in.params if business_object_in.params is not None else convert_from_dict(business_object.params)

        is_valid, errors = validate_parameters(sql_to_validate, params_to_validate)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Parameter validation failed",
                    "details": errors
                }
            )

    # Update fields
    update_data = business_object_in.model_dump(exclude_unset=True)
    # Convert params to dict if present
    if 'params' in update_data and update_data['params'] is not None:
        update_data['params'] = convert_to_dict(business_object_in.params)

    for field, value in update_data.items():
        setattr(business_object, field, value)

    db.commit()
    db.refresh(business_object)

    return business_object


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_business_object(
    id: UUID,
    db: Session = Depends(get_db)
) -> None:
    """
    Delete business object by ID.
    """
    business_object = db.query(BusinessObject).filter(BusinessObject.id == id).first()
    if not business_object:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business object with id {id} not found",
        )

    db.delete(business_object)
    db.commit()


@router.options("/{id}/test")
async def options_test_business_object(id: UUID) -> dict:
    """Handle preflight CORS request for test endpoint."""
    return {}


@router.post("/{id}/test", response_model=BusinessObjectTestResponse)
def test_business_object(
    id: UUID,
    test_request: BusinessObjectTestRequest,
    db: Session = Depends(get_db)
) -> BusinessObjectTestResponse:
    """
    Execute business object for testing.

    Process:
    1. Fetch business object by ID
    2. Decode SQL from BASE64
    3. Replace placeholders :parameter with provided values (uses param definitions for typing)
    4. Fetch connection by connection_id
    5. Execute SQL on specified connection
    6. Return results or error
    """
    # 1. Fetch business object
    business_object = db.query(BusinessObject).filter(BusinessObject.id == id).first()
    if not business_object:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business object with id {id} not found",
        )

    # 2. Decode SQL from BASE64
    try:
        decoded_sql = base64.b64decode(business_object.sql_command).decode('utf-8')
    except Exception as e:
        return BusinessObjectTestResponse(
            success=False,
            error=f"Failed to decode SQL command: {str(e)}"
        )

    # 3. Replace placeholders with parameters
    from app.utils.parameter_validation import extract_sql_parameters

    # Detect which parameter format is used in the SQL
    colon_params = extract_sql_parameters(decoded_sql)  # Extracts :parameter format
    brace_params = extract_parameters(decoded_sql)       # Extracts {{parameter}} format

    if colon_params:
        # Use new :parameter format with type-aware replacement
        final_sql = replace_colon_parameters(decoded_sql, test_request.parameters, business_object)
    elif brace_params:
        # Use legacy {{parameter}} format
        final_sql = replace_parameters(decoded_sql, test_request.parameters)
    else:
        # No parameters to replace - use SQL as is
        final_sql = decoded_sql

    # 4. Fetch connection (accepts both ID and slug)
    from app.utils.slug import get_database_by_id_or_slug
    try:
        connection = get_database_by_id_or_slug(test_request.connection_id, db)
    except HTTPException:
        return BusinessObjectTestResponse(
            success=False,
            error=f"Connection with id or slug '{test_request.connection_id}' not found"
        )

    if connection.status.value != "active":
        return BusinessObjectTestResponse(
            success=False,
            error=f"Connection {connection.name} is not active"
        )

    # 5. Execute SQL on connection
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

                return BusinessObjectTestResponse(
                    success=True,
                    rows=rows,
                    row_count=len(rows)
                )
            else:
                # For INSERT/UPDATE/DELETE, commit and return affected rows
                conn.commit()
                return BusinessObjectTestResponse(
                    success=True,
                    rows=[],
                    row_count=result.rowcount
                )

    except Exception as e:
        error_message = str(e)

        # Clean up common error messages
        if "authentication" in error_message.lower() or "password" in error_message.lower():
            error_message = "Authentication failed - check connection credentials"
        elif "timeout" in error_message.lower():
            error_message = "Query timeout - operation took too long"
        elif "syntax" in error_message.lower():
            error_message = f"SQL syntax error: {error_message}"

        return BusinessObjectTestResponse(
            success=False,
            error=error_message
        )


@router.post("/execute", response_model=BusinessObjectTestResponse)
def execute_sql(
    request: ExecuteSqlRequest,
    db: Session = Depends(get_db)
) -> BusinessObjectTestResponse:
    """
    Execute generic SQL command on a specified connection.
    Supports both DML and DDL operations.

    Process:
    1. Fetch connection by ID or slug
    2. Execute SQL command on specified connection
    3. Return results or error
    """
    # 1. Fetch connection (accepts both ID and slug)
    from app.utils.slug import get_database_by_id_or_slug
    try:
        connection = get_database_by_id_or_slug(request.connection_id, db)
    except HTTPException:
        return BusinessObjectTestResponse(
            success=False,
            error=f"Connection with id or slug '{request.connection_id}' not found"
        )

    if connection.status.value != "active":
        return BusinessObjectTestResponse(
            success=False,
            error=f"Connection {connection.name} is not active"
        )

    # 2. Execute SQL on connection
    try:
        engine = create_engine(
            connection.connection_string,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
        )

        with engine.connect() as conn:
            result = conn.execute(text(request.sql_command))

            # Check if it's a SELECT query
            if result.returns_rows:
                rows = []
                for row in result:
                    # Convert row to dictionary
                    row_dict = dict(row._mapping)
                    # Convert non-serializable types to strings
                    for key, value in row_dict.items():
                        if not isinstance(value, (str, int, float, bool, type(None))):
                            row_dict[key] = str(value)
                    rows.append(row_dict)

                return BusinessObjectTestResponse(
                    success=True,
                    rows=rows,
                    row_count=len(rows)
                )
            else:
                # For DML/DDL commands, commit and return affected rows
                conn.commit()
                return BusinessObjectTestResponse(
                    success=True,
                    rows=[],
                    row_count=result.rowcount
                )

    except Exception as e:
        error_message = str(e)

        # Clean up common error messages
        if "authentication" in error_message.lower() or "password" in error_message.lower():
            error_message = "Authentication failed - check connection credentials"
        elif "timeout" in error_message.lower():
            error_message = "Query timeout - operation took too long"
        elif "syntax" in error_message.lower():
            error_message = f"SQL syntax error: {error_message}"

        return BusinessObjectTestResponse(
            success=False,
            error=error_message
        )
