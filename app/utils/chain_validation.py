"""
Validation utilities for execution chain integrity.

This module provides functions to validate execution chain configuration
at the time of creating/updating API resources.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.business_object import BusinessObject
from app.schemas.api_resource import ExecutionChainStep


class ChainValidationError(Exception):
    """Exception raised when chain validation fails."""
    pass


def validate_execution_chain(
    chain: list[ExecutionChainStep],
    db: Session
) -> tuple[bool, list[str]]:
    """
    Validate execution chain configuration.

    Validations:
    1. Chain is not empty
    2. Orders are sequential starting from 1
    3. All business objects exist
    4. Parameter mappings reference valid previous steps
    5. Variable sources reference valid step indices
    6. First step has no parameter mappings (uses request payload)

    Args:
        chain: List of execution chain steps
        db: Database session

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors: list[str] = []

    # 1. Check if chain is not empty
    if not chain or len(chain) == 0:
        errors.append("Execution chain cannot be empty")
        return False, errors

    # 2. Sort by order and validate sequential order
    sorted_steps = sorted(chain, key=lambda s: s.order)

    for i, step in enumerate(sorted_steps):
        expected_order = i + 1
        if step.order != expected_order:
            errors.append(
                f"Invalid step order. Expected sequential order starting from 1. "
                f"Step at index {i} has order {step.order}, expected {expected_order}"
            )

    # 3. Validate each step
    business_object_ids: set[UUID] = set()

    for step_index, step in enumerate(sorted_steps):
        step_errors = validate_step(step, step_index, sorted_steps, db)
        errors.extend(step_errors)
        business_object_ids.add(step.business_object_id)

    # 4. Check for duplicate business object usage (warning, not error)
    if len(business_object_ids) < len(sorted_steps):
        # This is just a warning, not blocking
        pass

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_step(
    step: ExecutionChainStep,
    step_index: int,
    all_steps: list[ExecutionChainStep],
    db: Session
) -> list[str]:
    """
    Validate a single step in the execution chain.

    Args:
        step: Step to validate
        step_index: Index of the step in the chain (0-based)
        all_steps: All steps in the chain
        db: Database session

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    # 1. Validate business object exists
    business_object = db.query(BusinessObject).filter(
        BusinessObject.id == step.business_object_id
    ).first()

    if not business_object:
        errors.append(
            f"Step {step.order}: Business object with id {step.business_object_id} not found"
        )
        return errors  # Cannot continue validation without BO

    # 2. Validate business object type matches
    if step.business_object_type != business_object.command_type.value:
        errors.append(
            f"Step {step.order}: Business object type mismatch. "
            f"Expected '{business_object.command_type.value}', got '{step.business_object_type}'"
        )

    # 3. First step should not have parameter mappings
    if step.order == 1:
        if step.parameter_mappings and len(step.parameter_mappings) > 0:
            errors.append(
                f"Step {step.order}: First step should not have parameter mappings. "
                "It receives parameters directly from request payload."
            )
    else:
        # 4. Validate parameter mappings for subsequent steps
        mapping_errors = validate_parameter_mappings(
            step,
            step_index,
            all_steps
        )
        errors.extend(mapping_errors)

    return errors


def validate_parameter_mappings(
    step: ExecutionChainStep,
    step_index: int,
    all_steps: list[ExecutionChainStep]
) -> list[str]:
    """
    Validate parameter mappings for a step.

    Args:
        step: Step to validate
        step_index: Index of the step (0-based)
        all_steps: All steps in the chain

    Returns:
        List of error messages
    """
    errors: list[str] = []

    for mapping in step.parameter_mappings:
        # 1. Validate sourceType
        if mapping.source_type not in ["static", "variable"]:
            errors.append(
                f"Step {step.order}, parameter '{mapping.parameter_name}': "
                f"Invalid sourceType '{mapping.source_type}'. Must be 'static' or 'variable'."
            )
            continue

        # 2. For variable type, validate stepIndex
        if mapping.source_type == "variable":
            if mapping.variable_source.step_index is None:
                errors.append(
                    f"Step {step.order}, parameter '{mapping.parameter_name}': "
                    "stepIndex is required for sourceType 'variable'"
                )
                continue

            # 3. Validate stepIndex references a previous step
            if mapping.variable_source.step_index >= step_index:
                errors.append(
                    f"Step {step.order}, parameter '{mapping.parameter_name}': "
                    f"stepIndex {mapping.variable_source.step_index} must reference a previous step "
                    f"(current step index is {step_index})"
                )

            # 4. Validate stepIndex is within bounds
            if mapping.variable_source.step_index < 0 or mapping.variable_source.step_index >= len(all_steps):
                errors.append(
                    f"Step {step.order}, parameter '{mapping.parameter_name}': "
                    f"stepIndex {mapping.variable_source.step_index} is out of bounds "
                    f"(valid range: 0 to {len(all_steps) - 1})"
                )

            # 5. Validate fieldName is not empty
            if not mapping.variable_source.field_name:
                errors.append(
                    f"Step {step.order}, parameter '{mapping.parameter_name}': "
                    "fieldName is required for sourceType 'variable'"
                )

        # 6. For static type, check if staticValue is provided
        if mapping.source_type == "static":
            if mapping.static_value is None or mapping.static_value == "":
                # This is just a warning - allow empty static values
                pass

    return errors


def validate_chain_for_resource(
    chain: list[ExecutionChainStep] | None,
    business_object_id: UUID,
    db: Session
) -> tuple[bool, list[str]]:
    """
    Validate execution chain for an API resource.

    This function ensures:
    1. If chain exists, it's valid
    2. If chain exists, first step's business_object_id matches the resource's business_object_id
    3. Chain is compatible with the resource configuration

    Args:
        chain: Execution chain (can be None for legacy resources)
        business_object_id: Business object ID from the resource
        db: Database session

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors: list[str] = []

    # If no chain, it's valid (legacy mode)
    if chain is None or len(chain) == 0:
        return True, []

    # Validate chain structure
    is_valid, chain_errors = validate_execution_chain(chain, db)
    errors.extend(chain_errors)

    # Validate first step matches resource's business_object_id
    if len(chain) > 0:
        first_step = sorted(chain, key=lambda s: s.order)[0]
        if first_step.business_object_id != business_object_id:
            errors.append(
                "First step's businessObjectId must match the resource's businessObjectId. "
                f"Expected {business_object_id}, got {first_step.business_object_id}"
            )

    is_valid = len(errors) == 0
    return is_valid, errors
