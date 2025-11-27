"""
Backup utility for generating SQL dumps with INSERT ON CONFLICT statements.
"""
import base64
import json
from typing import List
from sqlalchemy.orm import Session
from app.models.database import Database
from app.models.business_object import BusinessObject
from app.models.api_resource import ApiResource


def escape_sql_string(value: str | None) -> str:
    """Escape single quotes in SQL strings."""
    if value is None:
        return "NULL"
    # Escape single quotes by doubling them
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def generate_backup_sql(db: Session) -> str:
    """
    Generate SQL backup script for databases, business_objects, and api_resources tables.
    Uses INSERT ... ON CONFLICT (id) DO UPDATE to handle existing records.
    """
    databases = db.query(Database).order_by(Database.created_at).all()
    business_objects = db.query(BusinessObject).order_by(BusinessObject.created_at).all()
    api_resources = db.query(ApiResource).order_by(ApiResource.created_at).all()

    total_records = len(databases) + len(business_objects) + len(api_resources)

    sql_lines = [
        "-- ===================================================================",
        "-- Complete Database Backup (databases, business_objects, api_resources)",
        f"-- Generated: {databases[0].created_at.strftime('%Y-%m-%d %H:%M:%S') if databases else 'N/A'}",
        f"-- Total records: {total_records}",
        "-- ===================================================================",
        "",
        "-- Ensure enums exist",
        "DO $$ BEGIN",
        "    CREATE TYPE database_status AS ENUM ('active', 'inactive');",
        "EXCEPTION",
        "    WHEN duplicate_object THEN null;",
        "END $$;",
        "",
        "DO $$ BEGIN",
        "    CREATE TYPE command_type AS ENUM ('select', 'insert', 'update', 'delete');",
        "EXCEPTION",
        "    WHEN duplicate_object THEN null;",
        "END $$;",
        "",
    ]

    # === BACKUP DATABASES TABLE ===
    if databases:
        sql_lines.extend([
            "-- ===================================================================",
            "-- Databases Table",
            f"-- Total records: {len(databases)}",
            "-- ===================================================================",
            "",
        ])

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
    else:
        sql_lines.append("-- No databases to backup\n")

    # === BACKUP BUSINESS_OBJECTS TABLE ===
    if business_objects:
        sql_lines.extend([
            "-- ===================================================================",
            "-- Business Objects Table",
            f"-- Total records: {len(business_objects)}",
            "-- ===================================================================",
            "",
        ])

        for obj in business_objects:
            # Format values
            id_val = f"'{obj.id}'"
            name_val = escape_sql_string(obj.name)
            command_type_val = f"'{obj.command_type.value}'"
            sql_command_val = escape_sql_string(obj.sql_command)
            tags_val = escape_sql_string(json.dumps(obj.tags))
            params_val = escape_sql_string(json.dumps(obj.params))
            created_val = f"'{obj.created_at.isoformat()}'"
            updated_val = f"'{obj.updated_at.isoformat()}'"

            # Generate INSERT ON CONFLICT statement
            sql_lines.extend([
                f"-- Backup record: {obj.name}",
                "INSERT INTO business_objects (",
                "    id, name, command_type, sql_command, tags, params, created_at, updated_at",
                ") VALUES (",
                f"    {id_val}::uuid,",
                f"    {name_val},",
                f"    {command_type_val}::command_type,",
                f"    {sql_command_val},",
                f"    {tags_val}::jsonb,",
                f"    {params_val}::jsonb,",
                f"    {created_val}::timestamp with time zone,",
                f"    {updated_val}::timestamp with time zone",
                ")",
                "ON CONFLICT (id) DO UPDATE SET",
                f"    name = {name_val},",
                f"    command_type = {command_type_val}::command_type,",
                f"    sql_command = {sql_command_val},",
                f"    tags = {tags_val}::jsonb,",
                f"    params = {params_val}::jsonb,",
                f"    updated_at = {updated_val}::timestamp with time zone;",
                "",
            ])
    else:
        sql_lines.append("-- No business objects to backup\n")

    # === BACKUP API_RESOURCES TABLE ===
    if api_resources:
        sql_lines.extend([
            "-- ===================================================================",
            "-- API Resources Table",
            f"-- Total records: {len(api_resources)}",
            "-- ===================================================================",
            "",
        ])

        for resource in api_resources:
            # Format values
            id_val = f"'{resource.id}'"
            path_val = escape_sql_string(resource.path)
            method_val = escape_sql_string(resource.method)
            description_val = escape_sql_string(resource.description)
            is_active_val = str(resource.is_active).lower()
            business_object_id_val = f"'{resource.business_object_id}'"
            business_object_name_val = escape_sql_string(resource.business_object_name)
            business_object_params_val = escape_sql_string(json.dumps(resource.business_object_params))
            execution_chain_val = escape_sql_string(json.dumps(resource.execution_chain)) if resource.execution_chain else "NULL"
            created_val = f"'{resource.created_at.isoformat()}'"
            updated_val = f"'{resource.updated_at.isoformat()}'"

            # Generate INSERT ON CONFLICT statement
            sql_lines.extend([
                f"-- Backup record: {resource.path}",
                "INSERT INTO api_resources (",
                "    id, path, method, description, is_active, business_object_id, business_object_name, business_object_params, execution_chain, created_at, updated_at",
                ") VALUES (",
                f"    {id_val}::uuid,",
                f"    {path_val},",
                f"    {method_val},",
                f"    {description_val},",
                f"    {is_active_val},",
                f"    {business_object_id_val}::uuid,",
                f"    {business_object_name_val},",
                f"    {business_object_params_val}::jsonb,",
                f"    {execution_chain_val}" if execution_chain_val != "NULL" else f"    NULL",
                f"    {created_val}::timestamp with time zone,",
                f"    {updated_val}::timestamp with time zone",
                ")",
                "ON CONFLICT (id) DO UPDATE SET",
                f"    path = {path_val},",
                f"    method = {method_val},",
                f"    description = {description_val},",
                f"    is_active = {is_active_val},",
                f"    business_object_id = {business_object_id_val}::uuid,",
                f"    business_object_name = {business_object_name_val},",
                f"    business_object_params = {business_object_params_val}::jsonb,",
                f"    execution_chain = {execution_chain_val}" if execution_chain_val != "NULL" else f"    execution_chain = NULL",
                f"    updated_at = {updated_val}::timestamp with time zone;",
                "",
            ])
    else:
        sql_lines.append("-- No API resources to backup\n")

    sql_lines.extend([
        "-- ===================================================================",
        "-- Backup completed successfully",
        f"-- Total records processed: {total_records}",
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
