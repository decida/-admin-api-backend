from pydantic import BaseModel


class BackupResponse(BaseModel):
    """Response schema for backup endpoint."""

    sql_base64: str
    """SQL script encoded in base64"""

    size_mb: float
    """Size of the SQL script in megabytes"""

    size_bytes: int
    """Size of the SQL script in bytes"""

    total_records: int
    """Total number of database records in backup"""

    format: str = "sql"
    """Backup format (always 'sql')"""

    compression: str = "base64"
    """Compression type (always 'base64')"""
