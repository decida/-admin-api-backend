from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.database import Database
from app.schemas.database import DatabaseCreate, DatabaseResponse, DatabaseUpdate

router = APIRouter()


@router.get("/", response_model=list[DatabaseResponse])
def get_databases(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
) -> list[Database]:
    """
    Retrieve all databases.
    """
    databases = db.query(Database).offset(skip).limit(limit).all()
    return databases


@router.get("/{database_id}", response_model=DatabaseResponse)
def get_database(database_id: UUID, db: Session = Depends(get_db)) -> Database:
    """
    Get database by ID.
    """
    database = db.query(Database).filter(Database.id == database_id).first()
    if not database:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database with id {database_id} not found",
        )
    return database


@router.post("/", response_model=DatabaseResponse, status_code=status.HTTP_201_CREATED)
def create_database(database_in: DatabaseCreate, db: Session = Depends(get_db)) -> Database:
    """
    Create new database connection.
    """
    # Check if database with same name already exists
    existing_database = db.query(Database).filter(Database.name == database_in.name).first()
    if existing_database:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database with this name already exists",
        )

    database = Database(**database_in.model_dump())
    db.add(database)
    db.commit()
    db.refresh(database)
    return database


@router.patch("/{database_id}", response_model=DatabaseResponse)
def update_database(
    database_id: UUID, database_in: DatabaseUpdate, db: Session = Depends(get_db)
) -> Database:
    """
    Update database connection.
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
    return database


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