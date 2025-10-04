import re
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.database import Database


def generate_slug(name: str) -> str:
    """
    Generate a URL-friendly slug from a name.
    Converts to lowercase, replaces spaces and special chars with hyphens.
    """
    # Convert to lowercase and replace non-alphanumeric chars with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower())
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def generate_unique_slug(name: str, db: Session) -> str:
    """
    Generate a unique slug from a name.
    If slug exists, append a counter to make it unique.
    """
    base_slug = generate_slug(name)
    final_slug = base_slug
    counter = 1

    while db.query(Database).filter(Database.slug == final_slug).first():
        final_slug = f"{base_slug}-{counter}"
        counter += 1

    return final_slug


def get_database_by_id_or_slug(id_or_slug: str, db: Session) -> Database:
    """
    Get database by ID (if UUID) or slug (if alphanumeric string).
    Raises 404 if not found.
    """
    database: Optional[Database] = None

    # Try to parse as UUID (numeric ID)
    try:
        database_id = UUID(id_or_slug)
        database = db.query(Database).filter(Database.id == database_id).first()
    except ValueError:
        # Not a valid UUID, treat as slug
        database = db.query(Database).filter(Database.slug == id_or_slug).first()

    if not database:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database with id or slug '{id_or_slug}' not found",
        )

    return database
