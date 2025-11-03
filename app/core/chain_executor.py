"""
Chain execution service for sequential business object execution.

This module handles the execution of execution chains, where multiple
business objects are executed sequentially with parameter mapping between steps.
"""

import base64
import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.business_object import BusinessObject
from app.models.database import Database
from app.schemas.api_resource import ExecutionChainStep, ParameterMapping

logger = logging.getLogger(__name__)


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
) -> dict | list:
    """
    Execute a business object SQL command.

    Args:
        business_object: Business object to execute
        parameters: Parameters for SQL execution
        connection: Database connection
        business_object_params: Parameter definitions

    Returns:
        Execution result (dict for INSERT/UPDATE/DELETE, list for SELECT)

    Raises:
        ChainExecutionException: If execution fails
    """
    from app.core.dynamic_routes import replace_colon_parameters

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
        engine = create_engine(
            connection.connection_string,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
        )

        logger.info(f"Creating connection and executing SQL...")
        with engine.connect() as conn:
            logger.info(f"Connection created, executing text command")
            result = conn.execute(text(final_sql))
            logger.info(f"SQL executed successfully, result type: {type(result)}")

            # For SELECT queries, fetch results
            if business_object.command_type.value == "select":
                logger.info(f"Processing SELECT query results")
                rows = []
                for row in result:
                    # Convert row to dictionary
                    row_dict = dict(row._mapping)
                    # Convert non-serializable types to strings
                    for key, value in row_dict.items():
                        if not isinstance(value, (str, int, float, bool, type(None))):
                            row_dict[key] = str(value)
                    rows.append(row_dict)
                logger.info(f"SELECT returned {len(rows)} rows")
                return rows

            elif business_object.command_type.value == "insert":
                logger.info(f"Processing INSERT command")
                # For INSERT, try to get inserted ID
                # Try to get last inserted ID (PostgreSQL specific)
                try:
                    # Check if SQL has RETURNING clause
                    if "RETURNING" in final_sql.upper():
                        logger.info(f"INSERT has RETURNING clause, reading results")
                        rows = []
                        for row in result:
                            row_dict = dict(row._mapping)
                            for key, value in row_dict.items():
                                if not isinstance(value, (str, int, float, bool, type(None))):
                                    row_dict[key] = str(value)
                            rows.append(row_dict)
                        logger.info(f"RETURNING clause returned {len(rows)} rows: {rows}")
                        # Commit after consuming results
                        logger.info(f"Committing transaction")
                        conn.commit()
                        if rows and len(rows) > 0:
                            # If RETURNING returned an id field, use it
                            if 'id' in rows[0]:
                                logger.info(f"Returning insertedId from RETURNING clause: {rows[0]['id']}")
                                return {"insertedId": rows[0]['id']}
                        # Fallback: return rowcount
                        logger.info(f"Returning rowcount: {result.rowcount}")
                        return {"insertedId": result.rowcount}
                    else:
                        # No RETURNING clause, just get rowcount before commit
                        logger.info(f"INSERT without RETURNING clause, getting rowcount")
                        rowcount = result.rowcount
                        logger.info(f"Rowcount: {rowcount}, committing transaction")
                        conn.commit()
                        logger.info(f"Transaction committed, returning rowcount")
                        return {"insertedId": rowcount}
                except Exception as e:
                    logger.error(f"Error processing INSERT result: {str(e)}", exc_info=True)
                    rowcount = result.rowcount
                    logger.info(f"Fallback: getting rowcount {rowcount}")
                    conn.commit()
                    return {"insertedId": rowcount}

            else:
                logger.info(f"Processing {business_object.command_type.value.upper()} command")
                # For UPDATE/DELETE, return affected rows
                rowcount = result.rowcount
                logger.info(f"Rowcount: {rowcount}, committing transaction")
                conn.commit()
                logger.info(f"Transaction committed, returning affected rows")
                return {"affectedRows": rowcount}

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
    logger.info(f"=" * 80)
    logger.info(f"Starting execution chain with {len(chain)} steps")
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
    step_results: list[Any] = []

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
            result = execute_business_object_sql(
                business_object,
                parameters,
                connection,
                bo_params
            )

            logger.info(f"Step {step.order} - Execution completed successfully")
            logger.info(f"Step {step.order} - Result: {result}")

            # Store result
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

    # Return results
    logger.info(f"=" * 80)
    logger.info(f"Execution chain completed successfully")
    logger.info(f"Total steps executed: {len(step_results)}")
    logger.info(f"Final result: {step_results[-1] if step_results else None}")
    logger.info(f"=" * 80)

    return {
        "success": True,
        "steps": len(step_results),
        "result": step_results[-1] if step_results else None,
        "allResults": step_results
    }
