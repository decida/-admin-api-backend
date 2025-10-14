"""
Utility functions for SQL parameter extraction and validation.
"""
import base64
import re
from typing import Any

from app.schemas.business_object import SqlParameter


def extract_sql_parameters(sql_command: str) -> set[str]:
    """
    Extract parameter names from SQL command.
    Parameters are in the format :paramName.

    Args:
        sql_command: SQL command string (may be BASE64 encoded or plain text)

    Returns:
        Set of unique parameter names (without the colon prefix)

    Example:
        >>> extract_sql_parameters("SELECT * FROM users WHERE id = :userId AND status = :status")
        {'userId', 'status'}
    """
    # Try to decode from BASE64 if needed
    try:
        decoded_sql = base64.b64decode(sql_command).decode('utf-8')
    except Exception:
        # If decoding fails, assume it's already plain text
        decoded_sql = sql_command

    # Extract parameters using regex: :paramName
    # Pattern: colon followed by letter/underscore, then alphanumeric/underscore
    pattern = r':([a-zA-Z_][a-zA-Z0-9_]*)'
    matches = re.findall(pattern, decoded_sql)

    # Return unique parameter names
    return set(matches)


def validate_parameters(
    sql_command: str,
    params: list[SqlParameter]
) -> tuple[bool, list[str]]:
    """
    Validate that SQL parameters match the parameter definitions.

    Validation rules:
    1. All parameters in SQL must have definitions in params array
    2. All parameters defined in params must be used in SQL
    3. Parameter names must be unique in params array

    Args:
        sql_command: SQL command string (may be BASE64 encoded)
        params: List of parameter definitions

    Returns:
        Tuple of (is_valid, error_messages)
        - is_valid: True if validation passes, False otherwise
        - error_messages: List of error messages (empty if valid)

    Example:
        >>> sql = "SELECT * FROM users WHERE id = :userId"
        >>> params = [SqlParameter(name="userId", type="number", required=True)]
        >>> validate_parameters(sql, params)
        (True, [])
    """
    errors: list[str] = []

    # Extract parameters from SQL
    sql_params = extract_sql_parameters(sql_command)

    # Get parameter names from definitions
    defined_params = {param.name for param in params}

    # Check for duplicate parameter names in definitions
    param_names = [param.name for param in params]
    duplicates = {name for name in param_names if param_names.count(name) > 1}
    if duplicates:
        errors.append(f"Duplicate parameter definitions found: {', '.join(sorted(duplicates))}")

    # Check for parameters in SQL but not defined
    missing_definitions = sql_params - defined_params
    if missing_definitions:
        missing_list = ', '.join(f"':{name}'" for name in sorted(missing_definitions))
        errors.append(f"Parameter(s) {missing_list} found in SQL but not defined in params array")

    # Check for defined parameters not used in SQL
    unused_params = defined_params - sql_params
    if unused_params:
        unused_list = ', '.join(f"'{name}'" for name in sorted(unused_params))
        errors.append(f"Parameter(s) {unused_list} defined in params but not used in SQL command")

    is_valid = len(errors) == 0
    return is_valid, errors


def convert_to_dict(params: list[SqlParameter]) -> list[dict[str, Any]]:
    """
    Convert list of SqlParameter objects to list of dictionaries for JSON storage.

    Args:
        params: List of SqlParameter objects

    Returns:
        List of parameter dictionaries
    """
    return [param.model_dump(by_alias=True) for param in params]


def convert_from_dict(params_data: list[dict[str, Any]]) -> list[SqlParameter]:
    """
    Convert list of parameter dictionaries to list of SqlParameter objects.

    Args:
        params_data: List of parameter dictionaries

    Returns:
        List of SqlParameter objects
    """
    return [SqlParameter(**param) for param in params_data]
