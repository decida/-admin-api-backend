from collections.abc import Generator
from urllib.parse import quote, urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings


def encode_database_url(database_url: str) -> str:
    """
    Encode special characters in database URL credentials.

    Parses the database URL and applies URL encoding to username and password
    to handle special characters (like @, :, %, etc.) that could break the connection string.

    Args:
        database_url: The raw database URL from environment variable

    Returns:
        The database URL with properly encoded credentials

    Example:
        Input:  "postgresql://user:p@ss%word@localhost:5432/dbname"
        Output: "postgresql://user:p%40ss%25word@localhost:5432/dbname"
    """
    parsed = urlparse(database_url)

    if parsed.username:
        # URL encode username and password, safe='' to encode all special chars
        encoded_username = quote(parsed.username, safe="")
        encoded_password = (
            quote(parsed.password, safe="") if parsed.password else ""
        )

        # Reconstruct netloc with encoded credentials
        if encoded_password:
            netloc = f"{encoded_username}:{encoded_password}@{parsed.hostname}"
        else:
            netloc = f"{encoded_username}@{parsed.hostname}"

        # Add port if present
        if parsed.port:
            netloc += f":{parsed.port}"

        # Reconstruct the URL
        return urlunparse(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

    return database_url


# Create engine
engine = create_engine(
    encode_database_url(settings.DATABASE_URL),
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()