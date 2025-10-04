import time

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_connection_string, encrypt_connection_string
from app.core.cache import (
    get_cache,
    set_cache,
    cache_key_database_list,
    cache_key_database,
    invalidate_database_cache,
)
from app.db.session import get_db
from app.models.database import Database
from app.schemas.database import (
    DatabaseCreate,
    DatabaseResponse,
    DatabaseTestConnection,
    DatabaseTestConnectionResponse,
    DatabaseUpdate,
)
from app.schemas.backup import BackupResponse
from app.utils.slug import generate_unique_slug, get_database_by_id_or_slug
from app.utils.backup import generate_backup_sql, encode_sql_to_base64, calculate_size_mb

router = APIRouter()


@router.get("/", response_model=list[DatabaseResponse])
async def get_databases(
    response: Response,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> list[DatabaseResponse]:
    """
    Retrieve all databases with encrypted connection strings.
    Results are cached for performance.
    Returns X-Cache-Status header: HIT (from cache) or MISS (from database).
    """
    # Try to get from cache
    cache_key = cache_key_database_list(skip, limit)
    cached = await get_cache(cache_key)
    if cached:
        response.headers["X-Cache-Status"] = "HIT"
        return [DatabaseResponse(**item) for item in cached]

    # Get from database
    databases = db.query(Database).offset(skip).limit(limit).all()

    # Encrypt connection strings before returning
    result = []
    for database in databases:
        db_dict = {
            "id": str(database.id),
            "name": database.name,
            "slug": database.slug,
            "type": database.type,
            "connection_string": encrypt_connection_string(database.connection_string),
            "description": database.description,
            "status": database.status,
            "created_at": database.created_at.isoformat(),
            "updated_at": database.updated_at.isoformat(),
        }
        result.append(DatabaseResponse(**db_dict))

    # Cache the result
    await set_cache(cache_key, [r.model_dump() for r in result])

    response.headers["X-Cache-Status"] = "MISS"
    return result


@router.get("/backup", response_model=BackupResponse)
async def backup_databases(db: Session = Depends(get_db)) -> BackupResponse:
    """
    Generate SQL backup of all database connections (base64 encoded).

    Returns:
    - sql_base64: Complete SQL script encoded in base64
    - size_mb: Size of the SQL in megabytes
    - size_bytes: Size of the SQL in bytes
    - total_records: Number of database records

    The SQL uses INSERT ... ON CONFLICT to safely restore data:
    - If record exists (same ID): updates all fields
    - If record doesn't exist: inserts new record

    To restore the backup:
    1. Decode base64: `echo "sql_base64" | base64 -d > backup.sql`
    2. Execute: `psql -h host -U user -d db -f backup.sql`

    For plain SQL download, use: GET /databases/backup/download
    """
    # Generate SQL backup
    sql_script = generate_backup_sql(db)

    # Encode to base64
    sql_base64 = encode_sql_to_base64(sql_script)

    # Calculate sizes
    size_mb = calculate_size_mb(sql_script)
    size_bytes = len(sql_script.encode('utf-8'))

    # Count records
    total_records = db.query(Database).count()

    return BackupResponse(
        sql_base64=sql_base64,
        size_mb=size_mb,
        size_bytes=size_bytes,
        total_records=total_records,
    )


@router.get("/backup/download")
async def download_backup_sql(db: Session = Depends(get_db)):
    """
    Download SQL backup as plain text file.

    Returns SQL script with proper content-type for download.
    The SQL uses INSERT ... ON CONFLICT for safe restoration.
    """
    from fastapi.responses import PlainTextResponse
    from datetime import datetime

    # Generate SQL backup
    sql_script = generate_backup_sql(db)

    # Return as downloadable file
    filename = f"databases_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

    return PlainTextResponse(
        content=sql_script,
        media_type="application/sql",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Backup-Size-MB": str(calculate_size_mb(sql_script)),
            "X-Backup-Records": str(db.query(Database).count()),
        }
    )


@router.get("/cache-debug")
async def cache_debug():
    """Debug endpoint to test Redis cache connection."""
    from app.core.config import settings
    from app.core.cache import get_cache, set_cache

    debug_info = {
        "redis_config": {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
            "password_set": bool(settings.REDIS_PASSWORD),
            "cache_ttl": settings.CACHE_TTL,
        },
        "tests": {}
    }

    try:
        # Test SET
        test_key = "debug:test"
        test_value = {"test": "data", "timestamp": "now"}
        set_result = await set_cache(test_key, test_value, ttl=60)
        debug_info["tests"]["set"] = {"success": set_result, "key": test_key}

        # Test GET
        get_result = await get_cache(test_key)
        debug_info["tests"]["get"] = {
            "success": get_result is not None,
            "value": get_result,
            "matches": get_result == test_value
        }

        # Test connection
        from app.core.cache import get_redis
        client = await get_redis()
        ping = await client.ping()
        debug_info["tests"]["ping"] = ping

        # Get info
        info = await client.info()
        debug_info["redis_info"] = {
            "redis_version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
        }

    except Exception as e:
        debug_info["error"] = str(e)
        debug_info["error_type"] = type(e).__name__

    return debug_info


@router.get("/{id_or_slug}", response_model=DatabaseResponse)
async def get_database(
    id_or_slug: str,
    response: Response,
    db: Session = Depends(get_db)
) -> DatabaseResponse:
    """
    Get database by ID (UUID) or slug with encrypted connection string.
    Result is cached for performance.
    Returns X-Cache-Status header: HIT (from cache) or MISS (from database).
    """
    # Try to get from cache
    cache_key = cache_key_database(id_or_slug)
    cached = await get_cache(cache_key)
    if cached:
        response.headers["X-Cache-Status"] = "HIT"
        return DatabaseResponse(**cached)

    # Get from database
    database = get_database_by_id_or_slug(id_or_slug, db)

    # Encrypt connection string before returning
    db_dict = {
        "id": str(database.id),
        "name": database.name,
        "slug": database.slug,
        "type": database.type,
        "connection_string": encrypt_connection_string(database.connection_string),
        "description": database.description,
        "status": database.status,
        "created_at": database.created_at.isoformat(),
        "updated_at": database.updated_at.isoformat(),
    }
    result = DatabaseResponse(**db_dict)

    # Cache the result
    await set_cache(cache_key, result.model_dump())

    response.headers["X-Cache-Status"] = "MISS"
    return result


@router.post("/", response_model=DatabaseResponse, status_code=status.HTTP_201_CREATED)
async def create_database(database_in: DatabaseCreate, db: Session = Depends(get_db)) -> DatabaseResponse:
    """
    Create new database connection.
    Connection string is stored as plain text in DB but returned encrypted.
    Slug is auto-generated from name and must be unique.
    Cache is invalidated after creation.
    """
    # Generate unique slug from name
    slug = generate_unique_slug(database_in.name, db)

    # Check if slug already exists (double-check for race conditions)
    existing_database = db.query(Database).filter(Database.slug == slug).first()
    if existing_database:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Database with slug '{slug}' already exists",
        )

    # Store connection string as plain text in DB
    database_data = database_in.model_dump()
    database_data["slug"] = slug
    database = Database(**database_data)
    db.add(database)
    db.commit()
    db.refresh(database)

    # Invalidate cache after creation
    await invalidate_database_cache()

    # Return with encrypted connection string
    db_dict = {
        "id": str(database.id),
        "name": database.name,
        "slug": database.slug,
        "type": database.type,
        "connection_string": encrypt_connection_string(database.connection_string),
        "description": database.description,
        "status": database.status,
        "created_at": database.created_at.isoformat(),
        "updated_at": database.updated_at.isoformat(),
    }
    return DatabaseResponse(**db_dict)


@router.patch("/{id_or_slug}", response_model=DatabaseResponse)
async def update_database(
    id_or_slug: str, database_in: DatabaseUpdate, db: Session = Depends(get_db)
) -> DatabaseResponse:
    """
    Update database connection by ID (UUID) or slug.
    Connection string is stored as plain text in DB but returned encrypted.
    Cache is invalidated after update.
    """
    database = get_database_by_id_or_slug(id_or_slug, db)

    update_data = database_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(database, field, value)

    db.commit()
    db.refresh(database)

    # Invalidate cache after update
    await invalidate_database_cache()

    # Return with encrypted connection string
    db_dict = {
        "id": str(database.id),
        "name": database.name,
        "slug": database.slug,
        "type": database.type,
        "connection_string": encrypt_connection_string(database.connection_string),
        "description": database.description,
        "status": database.status,
        "created_at": database.created_at.isoformat(),
        "updated_at": database.updated_at.isoformat(),
    }
    return DatabaseResponse(**db_dict)


@router.delete("/{id_or_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_database(id_or_slug: str, db: Session = Depends(get_db)) -> None:
    """
    Delete database connection by ID (UUID) or slug.
    Cache is invalidated after deletion.
    """
    database = get_database_by_id_or_slug(id_or_slug, db)

    db.delete(database)
    db.commit()

    # Invalidate cache after deletion
    await invalidate_database_cache()


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
            error_message = "Connection timeout (10s exceeded)"
        elif "authentication" in error_message.lower() or "password" in error_message.lower():
            error_message = "Authentication failed - check credentials"
        elif "host" in error_message.lower() or "connection refused" in error_message.lower():
            error_message = "Cannot reach database host - check host and port"

        return DatabaseTestConnectionResponse(
            success=False,
            message=f"Connection failed: {error_message}",
            latency_ms=round(latency_ms, 2),
        )