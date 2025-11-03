"""
Datetime formatting utilities for handling database-specific date/time formats.

This module provides utilities to properly format datetime values for different
database types, particularly for SQL Server compatibility.
"""

from datetime import datetime
from typing import Any


def format_datetime_for_sql(value: Any, db_type: str = "tsql") -> str:
    """
    Format a datetime value for SQL execution.

    Converts datetime objects to the appropriate string format for the database.
    SQL Server requires ISO 8601 format (YYYY-MM-DDTHH:MM:SS.fff) or CAST statements.

    Args:
        value: The value to format (datetime, string, or other)
        db_type: Database type ("tsql", "postgresql", "mysql"). Defaults to "tsql"

    Returns:
        Formatted string suitable for SQL insertion

    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 11, 3, 18, 24, 53, 653000)
        >>> format_datetime_for_sql(dt, "tsql")
        '2025-11-03T18:24:53.653'
    """
    if isinstance(value, datetime):
        if db_type.lower() in ["tsql", "mssql", "sql_server"]:
            # SQL Server prefers ISO 8601 format with T separator
            # and microseconds as milliseconds (3 digits)
            return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        else:
            # PostgreSQL and MySQL typically accept ISO 8601 with space
            return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    # If already a string, ensure it's valid ISO format
    if isinstance(value, str):
        # Already a string, return as-is
        return value

    # For other types, convert to string
    return str(value)


def serialize_datetime(value: Any, db_type: str = "tsql") -> str:
    """
    Serialize a datetime value for JSON response.

    Converts datetime objects to ISO 8601 string format for API responses.

    Args:
        value: The value to serialize (datetime, string, or other)
        db_type: Database type (not used for serialization, kept for consistency)

    Returns:
        ISO 8601 formatted string

    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 11, 3, 18, 24, 53, 653000)
        >>> serialize_datetime(dt)
        '2025-11-03T18:24:53.653000'
    """
    if isinstance(value, datetime):
        # ISO 8601 format with microseconds
        return value.isoformat()

    if isinstance(value, str):
        return value

    return str(value)
