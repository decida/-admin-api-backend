import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_connection_string, encrypt_connection_string
from app.db.session import get_db
from app.models.database import Database
from app.schemas.database import (
    DatabaseCreate,
    DatabaseResponse,
    DatabaseTestConnection,
    DatabaseTestConnectionResponse,
    DatabaseUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[DatabaseResponse])
def get_databases(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
) -> list[DatabaseResponse]:
    """
    Retrieve all databases with encrypted connection strings.
    """
    databases = db.query(Database).offset(skip).limit(limit).all()

    # Encrypt connection strings before returning
    response = []
    for database in databases:
        db_dict = {
            "id": database.id,
            "name": database.name,
            "type": database.type,
            "connection_string": encrypt_connection_string(database.connection_string),
            "description": database.description,
            "status": database.status,
            "created_at": database.created_at,
            "updated_at": database.updated_at,
        }
        response.append(DatabaseResponse(**db_dict))

    return response


@router.get("/{database_id}", response_model=DatabaseResponse)
def get_database(database_id: UUID, db: Session = Depends(get_db)) -> DatabaseResponse:
    """
    Get database by ID with encrypted connection string.
    """
    database = db.query(Database).filter(Database.id == database_id).first()
    if not database:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database with id {database_id} not found",
        )

    # Encrypt connection string before returning
    db_dict = {
        "id": database.id,
        "name": database.name,
        "type": database.type,
        "connection_string": encrypt_connection_string(database.connection_string),
        "description": database.description,
        "status": database.status,
        "created_at": database.created_at,
        "updated_at": database.updated_at,
    }
    return DatabaseResponse(**db_dict)


@router.post("/", response_model=DatabaseResponse, status_code=status.HTTP_201_CREATED)
def create_database(database_in: DatabaseCreate, db: Session = Depends(get_db)) -> DatabaseResponse:
    """
    Create new database connection.
    Connection string is stored as plain text in DB but returned encrypted.
    """
    # Check if database with same name already exists
    existing_database = db.query(Database).filter(Database.name == database_in.name).first()
    if existing_database:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database with this name already exists",
        )

    # Store connection string as plain text in DB
    database = Database(**database_in.model_dump())
    db.add(database)
    db.commit()
    db.refresh(database)

    # Return with encrypted connection string
    db_dict = {
        "id": database.id,
        "name": database.name,
        "type": database.type,
        "connection_string": encrypt_connection_string(database.connection_string),
        "description": database.description,
        "status": database.status,
        "created_at": database.created_at,
        "updated_at": database.updated_at,
    }
    return DatabaseResponse(**db_dict)


@router.patch("/{database_id}", response_model=DatabaseResponse)
def update_database(
    database_id: UUID, database_in: DatabaseUpdate, db: Session = Depends(get_db)
) -> DatabaseResponse:
    """
    Update database connection.
    Connection string is stored as plain text in DB but returned encrypted.
    """
    database = db.query(Database).filter(Database.id == database_id).first()
    if not database:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database with id {database_id} not found",
        )

    update_data = database_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(database, field, value)

    db.commit()
    db.refresh(database)

    # Return with encrypted connection string
    db_dict = {
        "id": database.id,
        "name": database.name,
        "type": database.type,
        "connection_string": encrypt_connection_string(database.connection_string),
        "description": database.description,
        "status": database.status,
        "created_at": database.created_at,
        "updated_at": database.updated_at,
    }
    return DatabaseResponse(**db_dict)


@router.delete("/{database_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_database(database_id: UUID, db: Session = Depends(get_db)) -> None:
    """
    Delete database connection.
    """
    database = db.query(Database).filter(Database.id == database_id).first()
    if not database:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database with id {database_id} not found",
        )

    db.delete(database)
    db.commit()


@router.post("/ping", response_model=DatabaseTestConnectionResponse)
def test_database_connection(
    connection_data: DatabaseTestConnection,
) -> DatabaseTestConnectionResponse:
    """
    Test database connection with 10 second timeout.
    Supports PostgreSQL, MySQL, SQLite, and other SQLAlchemy-compatible databases.
    """
    start_time = time.time()

    try:
        # Create engine with 10 second connection timeout
        engine = create_engine(
            connection_data.connection_string,
            connect_args={"connect_timeout": 10},
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
        )

        # Test the connection with a simple query
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        latency_ms = (time.time() - start_time) * 1000

        return DatabaseTestConnectionResponse(
            success=True,
            message=f"Connection successful to {connection_data.type} database",
            latency_ms=round(latency_ms, 2),
        )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        error_message = str(e)

        # Clean up error message for common issues
        if "timeout" in error_message.lower():
            error_message = "Connection timeout (15s exceeded)"
        elif "authentication" in error_message.lower() or "password" in error_message.lower():
            error_message = "Authentication failed - check credentials"
        elif "host" in error_message.lower() or "connection refused" in error_message.lower():
            error_message = "Cannot reach database host - check host and port"

        return DatabaseTestConnectionResponse(
            success=False,
            message=f"Connection failed: {error_message}",
            latency_ms=round(latency_ms, 2),
        )