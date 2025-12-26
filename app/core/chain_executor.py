"""
Chain execution service for sequential business object execution.

This module handles the execution of execution chains, where multiple
business objects are executed sequentially with parameter mapping between steps.
"""

import base64
import logging
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.business_object import BusinessObject
from app.models.database import Database
from app.schemas.api_resource import ExecutionChainStep, ParameterMapping
from app.core.engine_pool import get_engine_pool

logger = logging.getLogger(__name__)


def format_execution_time(start_time: datetime, end_time: datetime) -> str:
    """
    Format execution time summary.

    Args:
        start_time: Start datetime
        end_time: End datetime

    Returns:
        Formatted string like "Iniciou em 04/11/2025 as 09:50:01 e finalizou em 04/11/2025 as 09:51:02 totalizando 1 segundo"
    """
    start_str = start_time.strftime("%d/%m/%Y as %H:%M:%S")
    end_str = end_time.strftime("%d/%m/%Y as %H:%M:%S")

    # Calculate duration
    duration = end_time - start_time
    total_seconds = int(duration.total_seconds())

    # Format duration
    if total_seconds < 1:
        # Show milliseconds for very fast operations
        milliseconds = int(duration.total_seconds() * 1000)
        duration_str = f"{milliseconds} milissegundo(s)"
    elif total_seconds < 60:
        duration_str = f"{total_seconds} segundo(s)"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        duration_str = f"{minutes} minuto(s) e {seconds} segundo(s)"
    else:
        hours = total_seconds // 3600
        remaining = total_seconds % 3600
        minutes = remaining // 60
        seconds = remaining % 60
        duration_str = f"{hours} hora(s), {minutes} minuto(s) e {seconds} segundo(s)"

    return f"Iniciou em {start_str} e finalizou em {end_str} totalizando {duration_str}"


def clean_sql_command(sql: str) -> str:
    """
    Clean SQL command by removing line breaks and control characters.

    Converts multi-line SQL to single line for logging/display purposes.

    Args:
        sql: Raw SQL command

    Returns:
        Cleaned SQL command with normalized whitespace
    """
    # Replace all whitespace sequences (including newlines, tabs) with single space
    cleaned = re.sub(r'\s+', ' ', sql)
    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    return cleaned


class ChainExecutionException(Exception):
    """Exception raised during chain execution."""
    def __init__(
        self,
        message: str,
        step: int | None = None,
        business_object_name: str | None = None,
        details: str | None = None
    ):
        self.message = message
        self.step = step
        self.business_object_name = business_object_name
        self.details = details
        super().__init__(self.message)


def resolve_parameter_value(
    mapping: ParameterMapping,
    step_results: list[Any],
    request_payload: dict[str, Any]
) -> Any:
    """
    Resolve a parameter value based on mapping configuration.

    Args:
        mapping: Parameter mapping configuration
        step_results: List of results from previous steps
        request_payload: Original request payload

    Returns:
        Resolved parameter value

    Raises:
        ChainExecutionException: If variable field is not found
    """
    if mapping.source_type == "static":
        return mapping.static_value

    elif mapping.source_type == "variable":
        step_index = mapping.variable_source.step_index
        field_name = mapping.variable_source.field_name

        if step_index is None:
            raise ChainExecutionException(
                f"Variable source stepIndex is null for parameter '{mapping.parameter_name}'"
            )

        if step_index >= len(step_results):
            raise ChainExecutionException(
                f"Invalid stepIndex {step_index} for parameter '{mapping.parameter_name}'. Only {len(step_results)} steps executed so far."
            )

        source_result = step_results[step_index]

        # Handle different result types
        if isinstance(source_result, list):
            # For SELECT results (array of objects), use first row
            if len(source_result) == 0:
                raise ChainExecutionException(
                    f"Step {step_index + 1} returned no rows. Cannot extract field '{field_name}'"
                )
            source_data = source_result[0]
        elif isinstance(source_result, dict):
            # For INSERT/UPDATE/DELETE results (single object)
            source_data = source_result
        else:
            raise ChainExecutionException(
                f"Unexpected result type from step {step_index + 1}: {type(source_result)}"
            )

        # Extract field value
        if field_name not in source_data:
            raise ChainExecutionException(
                f"Field '{field_name}' not found in result of step {step_index + 1}. Available fields: {', '.join(source_data.keys())}"
            )

        return source_data[field_name]

    else:
        raise ChainExecutionException(
            f"Unknown sourceType '{mapping.source_type}' for parameter '{mapping.parameter_name}'"
        )


def build_step_parameters(
    step: ExecutionChainStep,
    step_index: int,
    step_results: list[Any],
    request_payload: dict[str, Any]
) -> dict[str, Any]:
    """
    Build parameters for a step based on its configuration.

    Args:
        step: Execution chain step configuration
        step_index: Current step index (0-based)
        step_results: Results from previous steps
        request_payload: Original request payload

    Returns:
        Dictionary of resolved parameters

    Raises:
        ChainExecutionException: If parameter resolution fails
    """
    if step.order == 1:
        # First step: use request payload directly
        return request_payload

    # Subsequent steps: resolve parameter mappings
    parameters = {}
    for mapping in step.parameter_mappings:
        try:
            parameters[mapping.parameter_name] = resolve_parameter_value(
                mapping,
                step_results,
                request_payload
            )
        except ChainExecutionException as e:
            # Re-raise with step context
            raise ChainExecutionException(
                e.message,
                step=step.order,
                business_object_name=step.business_object_name,
                details=str(e)
            )

    return parameters


def execute_business_object_sql(
    business_object: BusinessObject,
    parameters: dict[str, Any],
    connection: Database,
    business_object_params: list[dict]
) -> tuple[dict | list, str, str]:
    """
    Execute a business object SQL command.

    Args:
        business_object: Business object to execute
        parameters: Parameters for SQL execution
        connection: Database connection
        business_object_params: Parameter definitions

    Returns:
        Tuple of (execution result, full SQL command with parameters, execution time summary)
        - result: dict for INSERT/UPDATE/DELETE, list for SELECT
        - sql: Complete SQL command with all parameters interpolated
        - execution_time: Formatted string with start, end, and total time

    Raises:
        ChainExecutionException: If execution fails
    """
    from app.core.dynamic_routes import replace_colon_parameters

    # Record start time
    start_time = datetime.now()

    # Decode SQL command
    try:
        decoded_sql = base64.b64decode(business_object.sql_command).decode('utf-8')
    except Exception as e:
        raise ChainExecutionException(
            f"Failed to decode SQL command: {str(e)}",
            details=str(e)
        )

    # Replace parameters
    try:
        final_sql = replace_colon_parameters(
            decoded_sql,
            parameters,
            business_object_params
        )
        logger.info(f"Executing SQL command: {business_object.command_type.value.upper()}")
        logger.info(f"Full SQL: {final_sql}")
    except Exception as e:
        raise ChainExecutionException(
            f"Failed to replace parameters: {str(e)}",
            details=str(e)
        )

    # Execute SQL
    try:
        # Check if SQL is a T-SQL block with multiple statements
        is_tsql_block = final_sql.strip().upper().startswith('DECLARE') or 'BEGIN TRANSACTION' in final_sql.upper()

        if is_tsql_block:
            logger.info(f"Detected T-SQL block with multiple statements, using NullPool engine")
            # For T-SQL blocks with multiple result sets, use NullPool (cached by engine pool manager)
            engine_pool = get_engine_pool()
            engine = engine_pool.get_engine(
                database_id=connection.id,
                connection_string=connection.connection_string,
                use_null_pool=True  # Special T-SQL requirements
            )

            raw_conn = None
            cursor = None
            try:
                raw_conn = engine.raw_connection()
                logger.info(f"Raw connection created for T-SQL block execution")
                cursor = raw_conn.cursor()

                # Execute the T-SQL block
                cursor.execute(final_sql)
                logger.info(f"T-SQL block executed successfully")

                # Fetch all result sets
                all_results = []
                has_more_results = True

                while has_more_results:
                    try:
                        # Only try to fetch if cursor.description exists (result set has columns)
                        if cursor.description is not None:
                            # This result set has columns (SELECT statement)
                            from app.utils.datetime_formatter import serialize_datetime
                            column_names = [desc[0] for desc in cursor.description]
                            logger.info(f"Fetching result set with columns: {column_names}")
                            try:
                                rows = cursor.fetchall()
                                result_set = []
                                for row in rows:
                                    row_dict = {}
                                    for i, desc in enumerate(cursor.description):
                                        col_name = desc[0]
                                        value = row[i]
                                        if not isinstance(value, (str, int, float, bool, type(None))):
                                            value = serialize_datetime(value)
                                        row_dict[col_name] = value
                                    result_set.append(row_dict)
                                all_results.append(result_set)
                                logger.info(f"Result set has {len(result_set)} rows")
                            except Exception as fetch_error:
                                logger.warning(f"Error fetching rows from result set: {str(fetch_error)}")
                        else:
                            logger.info(f"Result set has no columns (non-SELECT statement like UPDATE/DELETE)")
                    except Exception as e:
                        logger.warning(f"Error processing result set: {str(e)}")

                    # Try to get next result set
                    try:
                        has_more_results = cursor.nextset()
                        if has_more_results:
                            logger.info(f"Moving to next result set")
                        else:
                            logger.info(f"No more result sets")
                    except Exception as e:
                        logger.warning(f"Error moving to next result set (HY010 errors expected for non-SELECT): {str(e)}")
                        has_more_results = False

                # Record end time and format execution time
                end_time = datetime.now()
                execution_time = format_execution_time(start_time, end_time)

                # Return the last result set (usually the final SELECT)
                if all_results:
                    logger.info(f"Returning last result set from T-SQL block ({len(all_results)} total sets)")
                    return all_results[-1], final_sql, execution_time
                else:
                    logger.info(f"T-SQL block completed with no SELECT results")
                    return [], final_sql, execution_time

            finally:
                if cursor:
                    try:
                        cursor.close()
                    except Exception as e:
                        logger.warning(f"Error closing cursor: {str(e)}")
                if raw_conn:
                    try:
                        raw_conn.close()
                    except Exception as e:
                        logger.warning(f"Error closing connection: {str(e)}")
                # NOTE: Do NOT dispose engine - it's cached by engine pool manager
                # Engine will be disposed automatically when expired from cache

        # Regular SQL execution for non-T-SQL blocks
        engine_pool = get_engine_pool()
        engine = engine_pool.get_engine(
            database_id=connection.id,
            connection_string=connection.connection_string
        )

        logger.info(f"Creating connection and executing SQL...")
        with engine.connect() as conn:
            logger.info(f"Connection created, executing text command")
            result = conn.execute(text(final_sql))
            logger.info(f"SQL executed successfully, result type: {type(result)}")

            # For SELECT queries, fetch results
            if business_object.command_type.value == "select":
                from app.utils.datetime_formatter import serialize_datetime
                logger.info(f"Processing SELECT query results")
                rows = []
                for row in result:
                    # Convert row to dictionary
                    row_dict = dict(row._mapping)
                    # Convert non-serializable types to strings
                    for key, value in row_dict.items():
                        if not isinstance(value, (str, int, float, bool, type(None))):
                            row_dict[key] = serialize_datetime(value)
                    rows.append(row_dict)
                logger.info(f"SELECT returned {len(rows)} rows")

                # Record end time and format execution time
                end_time = datetime.now()
                execution_time = format_execution_time(start_time, end_time)

                return rows, final_sql, execution_time

            elif business_object.command_type.value == "insert":
                logger.info(f"Processing INSERT command")
                # For INSERT, try to get inserted ID
                try:
                    # Check if SQL has RETURNING clause
                    if "RETURNING" in final_sql.upper():
                        from app.utils.datetime_formatter import serialize_datetime
                        logger.info(f"INSERT has RETURNING clause, reading results")
                        rows = []
                        for row in result:
                            row_dict = dict(row._mapping)
                            for key, value in row_dict.items():
                                if not isinstance(value, (str, int, float, bool, type(None))):
                                    row_dict[key] = serialize_datetime(value)
                            rows.append(row_dict)
                        logger.info(f"RETURNING clause returned {len(rows)} rows: {rows}")
                        # Commit after consuming results
                        logger.info(f"Committing transaction")
                        conn.commit()

                        # Record end time and format execution time
                        end_time = datetime.now()
                        execution_time = format_execution_time(start_time, end_time)

                        if rows and len(rows) > 0:
                            # If RETURNING returned an id field, use it
                            if 'id' in rows[0]:
                                logger.info(f"Returning insertedId from RETURNING clause: {rows[0]['id']}")
                                return {"insertedId": rows[0]['id']}, final_sql, execution_time
                        # Fallback: return rowcount
                        logger.info(f"Returning rowcount: {result.rowcount}")
                        return {"insertedId": result.rowcount}, final_sql, execution_time
                    else:
                        # No RETURNING clause, just get rowcount before commit
                        logger.info(f"INSERT without RETURNING clause, getting rowcount")
                        rowcount = result.rowcount
                        logger.info(f"Rowcount: {rowcount}, committing transaction")
                        conn.commit()
                        logger.info(f"Transaction committed, returning rowcount")

                        # Record end time and format execution time
                        end_time = datetime.now()
                        execution_time = format_execution_time(start_time, end_time)

                        return {"insertedId": rowcount}, final_sql, execution_time
                except Exception as e:
                    logger.error(f"Error processing INSERT result: {str(e)}", exc_info=True)
                    rowcount = result.rowcount
                    logger.info(f"Fallback: getting rowcount {rowcount}")
                    conn.commit()

                    # Record end time and format execution time
                    end_time = datetime.now()
                    execution_time = format_execution_time(start_time, end_time)

                    return {"insertedId": rowcount}, final_sql, execution_time

            else:
                logger.info(f"Processing {business_object.command_type.value.upper()} command")
                # For UPDATE/DELETE, return affected rows
                rowcount = result.rowcount
                logger.info(f"Rowcount: {rowcount}, committing transaction")
                conn.commit()
                logger.info(f"Transaction committed, returning affected rows")

                # Record end time and format execution time
                end_time = datetime.now()
                execution_time = format_execution_time(start_time, end_time)

                return {"affectedRows": rowcount}, final_sql, execution_time

    except ChainExecutionException:
        raise
    except Exception as e:
        error_message = str(e)
        logger.error(f"SQL execution failed: {error_message}")
        raise ChainExecutionException(
            f"SQL execution failed: {error_message}",
            details=str(e)
        )


def execute_chain(
    chain: list[ExecutionChainStep],
    request_payload: dict[str, Any],
    connection_id: UUID,
    db: Session
) -> dict:
    """
    Execute a chain of business objects sequentially.

    Args:
        chain: List of execution chain steps
        request_payload: Request payload with parameters
        connection_id: Database connection ID
        db: Database session

    Returns:
        Dictionary with execution results:
        {
            "success": True,
            "steps": 3,
            "result": {...},  # Last step result
            "allResults": [...]  # All step results
        }

    Raises:
        ChainExecutionException: If execution fails at any step
    """
    # Record overall chain start time
    chain_start_time = datetime.now()

    logger.info(f"=" * 80)
    logger.info(f"Starting execution chain with {len(chain)} steps")
    logger.info(f"Chain started at: {chain_start_time.strftime('%d/%m/%Y as %H:%M:%S')}")
    logger.info(f"Connection ID: {connection_id}")

    # Fetch database connection (accepts both ID and slug)
    from app.utils.slug import get_database_by_id_or_slug
    try:
        connection = get_database_by_id_or_slug(connection_id, db)
        logger.info(f"Database connection found: {connection.name} (ID: {connection.id})")
    except HTTPException as e:
        logger.error(f"Connection with id or slug '{connection_id}' not found")
        raise ChainExecutionException(
            f"Connection with id or slug '{connection_id}' not found"
        )

    if connection.status.value != "active":
        logger.error(f"Connection '{connection.name}' is not active (status: {connection.status.value})")
        raise ChainExecutionException(
            f"Connection '{connection.name}' is not active"
        )

    logger.info(f"Connection is active, proceeding with chain execution")

    # Sort steps by order
    sorted_steps = sorted(chain, key=lambda s: s.order)
    logger.info(f"Steps sorted by order")

    # Validate sequential order
    for i, step in enumerate(sorted_steps):
        expected_order = i + 1
        if step.order != expected_order:
            logger.error(f"Invalid step order. Expected {expected_order}, got {step.order}")
            raise ChainExecutionException(
                f"Invalid step order. Expected {expected_order}, got {step.order}"
            )

    # Execute steps
    step_results: list[Any] = []  # Store raw results for chain parameter resolution
    step_details: list[dict] = []  # Store detailed step information

    for step_index, step in enumerate(sorted_steps):
        try:
            logger.info(f"=" * 80)
            logger.info(f"Executing step {step.order}/{len(sorted_steps)}: {step.business_object_name}")
            logger.info(f"Business Object ID: {step.business_object_id}")

            # Fetch business object
            business_object = db.query(BusinessObject).filter(
                BusinessObject.id == step.business_object_id
            ).first()

            if not business_object:
                raise ChainExecutionException(
                    f"Business object '{step.business_object_name}' not found",
                    step=step.order,
                    business_object_name=step.business_object_name
                )

            logger.info(f"Business object found - Command type: {business_object.command_type.value}")

            # Build parameters
            parameters = build_step_parameters(
                step,
                step_index,
                step_results,
                request_payload
            )

            logger.info(f"Step {step.order} - Resolved parameters: {parameters}")

            # Convert business_object_params to dict format for execution
            bo_params = [p.model_dump(by_alias=True) for p in step.business_object_params]

            # Execute business object
            logger.info(f"Step {step.order} - Executing business object...")
            result, full_sql, execution_time = execute_business_object_sql(
                business_object,
                parameters,
                connection,
                bo_params
            )

            logger.info(f"Step {step.order} - Execution completed successfully")
            logger.info(f"Step {step.order} - Result: {result}")
            logger.info(f"Step {step.order} - Execution time: {execution_time}")

            # Calculate total (rows for SELECT, affected rows for DML)
            if isinstance(result, list):
                # SELECT query: count rows in result
                total = len(result)
            elif isinstance(result, dict):
                # DML query: get affected/inserted rows
                if "affectedRows" in result:
                    total = result["affectedRows"]
                elif "insertedId" in result:
                    total = result["insertedId"] if isinstance(result["insertedId"], int) else 1
                else:
                    total = 0
            else:
                total = 0

            # Create detailed step information
            step_detail = {
                "sequence": step.order,
                "name": step.business_object_name,
                "command_type": business_object.command_type.value,
                "sql_command": clean_sql_command(full_sql),
                "output": result if isinstance(result, list) else None,
                "total": total,
                "execution_time": execution_time
            }
            step_details.append(step_detail)
            logger.info(f"Step {step.order} - Detail: {step_detail}")

            # Store raw result for chain parameter resolution
            step_results.append(result)
            logger.info(f"Step {step.order} - Result stored")

        except ChainExecutionException as e:
            # Add step context if not already present
            if e.step is None:
                e.step = step.order
            if e.business_object_name is None:
                e.business_object_name = step.business_object_name
            raise

        except Exception as e:
            raise ChainExecutionException(
                f"Unexpected error in step {step.order}: {str(e)}",
                step=step.order,
                business_object_name=step.business_object_name,
                details=str(e)
            )

    # Record overall chain end time and format
    chain_end_time = datetime.now()
    total_execution_time = format_execution_time(chain_start_time, chain_end_time)

    # Return results
    logger.info(f"=" * 80)
    logger.info(f"Execution chain completed successfully")
    logger.info(f"Total steps executed: {len(step_results)}")
    logger.info(f"Final result: {step_results[-1] if step_results else None}")
    logger.info(f"Chain execution time: {total_execution_time}")
    logger.info(f"=" * 80)

    return {
        "success": True,
        "steps": step_details,  # Detailed step information with results
        "total_execution_time": total_execution_time  # Overall chain execution time
    }
