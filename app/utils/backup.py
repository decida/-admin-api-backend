"""
Backup utility for generating SQL dumps with INSERT ON CONFLICT statements.
"""
import base64
from typing import List
from sqlalchemy.orm import Session
from app.models.database import Database


def escape_sql_string(value: str | None) -> str:
    """Escape single quotes in SQL strings."""
    if value is None:
        return "NULL"
    # Escape single quotes by doubling them
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def generate_backup_sql(db: Session) -> str:
    """
    Generate SQL backup script for databases table.
    Uses INSERT ... ON CONFLICT (id) DO UPDATE to handle existing records.
    """
    databases = db.query(Database).order_by(Database.created_at).all()

    if not databases:
        return "-- No databases to backup\n"

    sql_lines = [
        "-- ===================================================================",
        "-- Database Connections Backup",
        f"-- Generated: {databases[0].created_at.strftime('%Y-%m-%d %H:%M:%S') if databases else 'N/A'}",
        f"-- Total records: {len(databases)}",
        "-- ===================================================================",
        "",
        "-- Ensure database_status enum exists",
        "DO $$ BEGIN",
        "    CREATE TYPE database_status AS ENUM ('active', 'inactive');",
        "EXCEPTION",
        "    WHEN duplicate_object THEN null;",
        "END $$;",
        "",
    ]

    for database in databases:
        # Format values
        id_val = f"'{database.id}'"
        name_val = escape_sql_string(database.name)
        slug_val = escape_sql_string(database.slug)
        type_val = escape_sql_string(database.type)
        conn_str_val = escape_sql_string(database.connection_string)
        desc_val = escape_sql_string(database.description)
        status_val = f"'{database.status.value}'"
        created_val = f"'{database.created_at.isoformat()}'"
        updated_val = f"'{database.updated_at.isoformat()}'"

        # Generate INSERT ON CONFLICT statement
        sql_lines.extend([
            f"-- Backup record: {database.name} ({database.slug})",
            "INSERT INTO databases (",
            "    id, name, slug, type, connection_string, description, status, created_at, updated_at",
            ") VALUES (",
            f"    {id_val}::uuid,",
            f"    {name_val},",
            f"    {slug_val},",
            f"    {type_val},",
            f"    {conn_str_val},",
            f"    {desc_val},",
            f"    {status_val}::database_status,",
            f"    {created_val}::timestamp with time zone,",
            f"    {updated_val}::timestamp with time zone",
            ")",
            "ON CONFLICT (id) DO UPDATE SET",
            f"    name = {name_val},",
            f"    slug = {slug_val},",
            f"    type = {type_val},",
            f"    connection_string = {conn_str_val},",
            f"    description = {desc_val},",
            f"    status = {status_val}::database_status,",
            f"    updated_at = {updated_val}::timestamp with time zone;",
            "",
        ])

    sql_lines.extend([
        "-- ===================================================================",
        "-- Backup completed successfully",
        f"-- Total records processed: {len(databases)}",
        "-- ===================================================================",
    ])

    return "\n".join(sql_lines)


def encode_sql_to_base64(sql: str) -> str:
    """Encode SQL string to base64."""
    return base64.b64encode(sql.encode('utf-8')).decode('utf-8')


def calculate_size_mb(content: str) -> float:
    """Calculate size of string in megabytes."""
    size_bytes = len(content.encode('utf-8'))
    size_mb = size_bytes / (1024 * 1024)
    return round(size_mb, 4)
