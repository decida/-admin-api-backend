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
)

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
    """
    # Check if name already exists
    existing = db.query(BusinessObject).filter(BusinessObject.name == business_object_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Business object with name '{business_object_in.name}' already exists",
        )

    # Create business object
    business_object = BusinessObject(**business_object_in.model_dump())
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

    # Update fields
    update_data = business_object_in.model_dump(exclude_unset=True)
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
    3. Replace placeholders {{parameter}} with provided values
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

    # 3. Replace placeholders with parameters (all optional, missing = NULL)
    final_sql = replace_parameters(decoded_sql, test_request.parameters)

    # 4. Fetch connection
    connection = db.query(Database).filter(Database.id == test_request.connection_id).first()
    if not connection:
        return BusinessObjectTestResponse(
            success=False,
            error=f"Connection with id {test_request.connection_id} not found"
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
