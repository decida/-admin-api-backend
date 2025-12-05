from collections.abc import Generator
from urllib.parse import quote_plus, urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings


def encode_database_url(database_url: str) -> str:
    """Encode password in database URL to handle special characters."""
    parsed = urlparse(database_url)
    if not parsed.password:
        return database_url

    encoded_password = quote_plus(parsed.password)
    netloc = f"{parsed.username}:{encoded_password}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"

    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


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