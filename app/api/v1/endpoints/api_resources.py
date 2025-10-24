from uuid import UUID
import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.api_resource import ApiResource
from app.models.business_object import BusinessObject
from app.schemas.api_resource import (
    ApiResourceCreate,
    ApiResourceResponse,
    ApiResourceUpdate,
    ExecutionChainStep,
)
from app.utils.parameter_validation import convert_from_dict

router = APIRouter()


class ExecuteResourceRequest(BaseModel):
    """Request schema for generic resource execution."""
    resource_id: UUID = Field(..., description="API Resource UUID")
    connection_id: str = Field(..., description="Database connection ID (UUID) or slug")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Resource parameters")


def convert_params_to_camel_case(params: list[dict]) -> list[dict]:
    """Convert parameter dicts from snake_case to camelCase for API response."""
    result = []
    for param in params:
        converted = {
            "name": param.get("name"),
            "type": param.get("type"),
            "required": param.get("required", False),
            "defaultValue": param.get("default_value") or param.get("defaultValue")
        }
        result.append(converted)
    return result


def convert_execution_chain_to_json_serializable(chain: list[ExecutionChainStep] | None) -> list[dict] | None:
    """
    Convert execution chain to JSON-serializable dict format.
    Converts UUIDs to strings to avoid JSON serialization errors.
    """
    if chain is None:
        return None

    result = []
    for step in chain:
        # Convert step to dict with by_alias=True to get camelCase keys
        step_dict = step.model_dump(by_alias=True, mode='json')

        # Ensure businessObjectId is a string
        if 'businessObjectId' in step_dict and isinstance(step_dict['businessObjectId'], UUID):
            step_dict['businessObjectId'] = str(step_dict['businessObjectId'])

        result.append(step_dict)

    return result


def convert_execution_chain_to_camel_case(chain: list[dict] | None) -> list[dict] | None:
    """Convert execution chain from snake_case to camelCase for API response."""
    if chain is None:
        return None

    result = []
    for step in chain:
        # Convert parameter mappings
        mappings = []
        for mapping in step.get("parameterMappings", step.get("parameter_mappings", [])):
            var_source = mapping.get("variableSource", mapping.get("variable_source", {}))
            converted_mapping = {
                "parameterName": mapping.get("parameterName", mapping.get("parameter_name")),
                "sourceType": mapping.get("sourceType", mapping.get("source_type")),
                "staticValue": mapping.get("staticValue", mapping.get("static_value", "")),
                "variableSource": {
                    "stepIndex": var_source.get("stepIndex", var_source.get("step_index")),
                    "fieldName": var_source.get("fieldName", var_source.get("field_name", ""))
                }
            }
            mappings.append(converted_mapping)

        converted_step = {
            "businessObjectId": step.get("businessObjectId", step.get("business_object_id")),
            "businessObjectName": step.get("businessObjectName", step.get("business_object_name")),
            "businessObjectType": step.get("businessObjectType", step.get("business_object_type")),
            "businessObjectParams": convert_params_to_camel_case(
                step.get("businessObjectParams", step.get("business_object_params", []))
            ),
            "order": step.get("order"),
            "parameterMappings": mappings
        }
        result.append(converted_step)

    return result


@router.get("/", response_model=list[ApiResourceResponse])
def get_api_resources(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> list[ApiResourceResponse]:
    """
    Retrieve all API resources.
    Returns list with metadata including Business Object info.
    """
    api_resources = db.query(ApiResource).offset(skip).limit(limit).all()

    # Convert to response format with camelCase
    result = []
    for resource in api_resources:
        resource_dict = {
            "id": resource.id,
            "path": resource.path,
            "method": resource.method,
            "description": resource.description,
            "isActive": resource.is_active,
            "businessObjectId": resource.business_object_id,
            "businessObjectName": resource.business_object_name,
            "businessObjectParams": convert_params_to_camel_case(resource.business_object_params),
            "executionChain": convert_execution_chain_to_camel_case(resource.execution_chain),
            "createdAt": resource.created_at,
            "updatedAt": resource.updated_at,
        }
        result.append(ApiResourceResponse(**resource_dict))

    return result


@router.get("/{id}", response_model=ApiResourceResponse)
def get_api_resource(
    id: UUID,
    db: Session = Depends(get_db)
) -> ApiResourceResponse:
    """
    Get API resource by ID.
    Returns metadata including Business Object info.
    """
    api_resource = db.query(ApiResource).filter(ApiResource.id == id).first()
    if not api_resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API resource with id {id} not found",
        )

    # Convert to response format with camelCase
    resource_dict = {
        "id": api_resource.id,
        "path": api_resource.path,
        "method": api_resource.method,
        "description": api_resource.description,
        "isActive": api_resource.is_active,
        "businessObjectId": api_resource.business_object_id,
        "businessObjectName": api_resource.business_object_name,
        "businessObjectParams": convert_params_to_camel_case(api_resource.business_object_params),
        "executionChain": convert_execution_chain_to_camel_case(api_resource.execution_chain),
        "createdAt": api_resource.created_at,
        "updatedAt": api_resource.updated_at,
    }

    return ApiResourceResponse(**resource_dict)


@router.post("/", response_model=ApiResourceResponse, status_code=status.HTTP_201_CREATED)
def create_api_resource(
    api_resource_in: ApiResourceCreate,
    db: Session = Depends(get_db)
) -> ApiResourceResponse:
    """
    Create new API resource.

    Validations:
    - path must be unique
    - path must start with /
    - businessObjectId must exist
    - Copies name and params from Business Object as snapshot
    """
    # Check if path already exists
    existing = db.query(ApiResource).filter(ApiResource.path == api_resource_in.path).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"API resource with path '{api_resource_in.path}' already exists",
        )

    # Check if Business Object exists
    business_object = db.query(BusinessObject).filter(
        BusinessObject.id == api_resource_in.business_object_id
    ).first()
    if not business_object:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business object with id {api_resource_in.business_object_id} not found",
        )

    # Validate execution chain if provided
    if api_resource_in.execution_chain:
        from app.utils.chain_validation import validate_chain_for_resource

        is_valid, validation_errors = validate_chain_for_resource(
            api_resource_in.execution_chain,
            api_resource_in.business_object_id,
            db
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid execution chain: {'; '.join(validation_errors)}"
            )

    # Convert execution_chain to dict format for database storage
    execution_chain_data = convert_execution_chain_to_json_serializable(api_resource_in.execution_chain)

    # Create API resource with snapshot of Business Object metadata
    api_resource = ApiResource(
        path=api_resource_in.path,
        method="POST",  # Always POST for now
        description=api_resource_in.description,
        is_active=api_resource_in.is_active,
        business_object_id=api_resource_in.business_object_id,
        business_object_name=business_object.name,
        business_object_params=business_object.params,
        execution_chain=execution_chain_data,
    )

    db.add(api_resource)
    db.commit()
    db.refresh(api_resource)

    # Convert to response format with camelCase
    resource_dict = {
        "id": api_resource.id,
        "path": api_resource.path,
        "method": api_resource.method,
        "description": api_resource.description,
        "isActive": api_resource.is_active,
        "businessObjectId": api_resource.business_object_id,
        "businessObjectName": api_resource.business_object_name,
        "businessObjectParams": convert_params_to_camel_case(api_resource.business_object_params),
        "executionChain": convert_execution_chain_to_camel_case(api_resource.execution_chain),
        "createdAt": api_resource.created_at,
        "updatedAt": api_resource.updated_at,
    }

    return ApiResourceResponse(**resource_dict)


@router.patch("/{id}", response_model=ApiResourceResponse)
def update_api_resource(
    id: UUID,
    api_resource_in: ApiResourceUpdate,
    db: Session = Depends(get_db)
) -> ApiResourceResponse:
    """
    Update API resource.
    If businessObjectId is changed, updates the snapshot metadata.
    """
    api_resource = db.query(ApiResource).filter(ApiResource.id == id).first()
    if not api_resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API resource with id {id} not found",
        )

    # Check if path already exists (if being updated)
    if api_resource_in.path and api_resource_in.path != api_resource.path:
        existing = db.query(ApiResource).filter(ApiResource.path == api_resource_in.path).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"API resource with path '{api_resource_in.path}' already exists",
            )

    # If businessObjectId is being updated, validate and update snapshot
    if api_resource_in.business_object_id:
        business_object = db.query(BusinessObject).filter(
            BusinessObject.id == api_resource_in.business_object_id
        ).first()
        if not business_object:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business object with id {api_resource_in.business_object_id} not found",
            )

        # Update Business Object snapshot
        api_resource.business_object_id = api_resource_in.business_object_id
        api_resource.business_object_name = business_object.name
        api_resource.business_object_params = business_object.params

    # Update other fields
    update_data = api_resource_in.model_dump(exclude_unset=True, exclude={'business_object_id', 'execution_chain'})
    for field, value in update_data.items():
        # Convert camelCase to snake_case
        if field == 'isActive':
            setattr(api_resource, 'is_active', value)
        else:
            setattr(api_resource, field, value)

    # Handle execution_chain update separately
    if api_resource_in.execution_chain is not None:
        from app.utils.chain_validation import validate_chain_for_resource

        # Determine which business_object_id to use for validation
        bo_id_to_validate = (
            api_resource_in.business_object_id
            if api_resource_in.business_object_id
            else api_resource.business_object_id
        )

        is_valid, validation_errors = validate_chain_for_resource(
            api_resource_in.execution_chain,
            bo_id_to_validate,
            db
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid execution chain: {'; '.join(validation_errors)}"
            )

        execution_chain_data = convert_execution_chain_to_json_serializable(api_resource_in.execution_chain)
        api_resource.execution_chain = execution_chain_data

    db.commit()
    db.refresh(api_resource)

    # Convert to response format with camelCase
    resource_dict = {
        "id": api_resource.id,
        "path": api_resource.path,
        "method": api_resource.method,
        "description": api_resource.description,
        "isActive": api_resource.is_active,
        "businessObjectId": api_resource.business_object_id,
        "businessObjectName": api_resource.business_object_name,
        "businessObjectParams": convert_params_to_camel_case(api_resource.business_object_params),
        "executionChain": convert_execution_chain_to_camel_case(api_resource.execution_chain),
        "createdAt": api_resource.created_at,
        "updatedAt": api_resource.updated_at,
    }

    return ApiResourceResponse(**resource_dict)


@router.post("/execute", status_code=status.HTTP_200_OK)
async def execute_resource(
    request: ExecuteResourceRequest = Body(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generic endpoint to execute any API resource.

    This endpoint accepts:
    - resource_id: UUID of the API resource to execute
    - connection_id: Database connection ID (UUID) or slug (string)
    - parameters: Dictionary with resource-specific parameters

    Returns the execution result (rows for SELECT, rowCount for DML, or chain results).

    Example request:
    {
        "resource_id": "abc-123-def",
        "connection_id": "my-postgres-db",
        "parameters": {
            "param1": "value1",
            "param2": 123
        }
    }
    """
    # Import here to avoid circular dependency
    from app.core.dynamic_routes import execute_dynamic_endpoint_logic

    # Fetch API resource
    api_resource = db.query(ApiResource).filter(ApiResource.id == request.resource_id).first()
    if not api_resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API resource with id {request.resource_id} not found"
        )

    # Validate it's active
    if not api_resource.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API resource is not active"
        )

    # Execute resource using existing logic
    result = await execute_dynamic_endpoint_logic(
        api_resource=api_resource,
        connection_id=request.connection_id,
        parameters=request.parameters,
        db=db
    )

    return result


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_resource(
    id: UUID,
    db: Session = Depends(get_db)
) -> None:
    """
    Delete API resource by ID.
    Removes the dynamic route from the system.
    """
    api_resource = db.query(ApiResource).filter(ApiResource.id == id).first()
    if not api_resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API resource with id {id} not found",
        )

    db.delete(api_resource)
    db.commit()


@router.patch("/{id}/toggle", response_model=ApiResourceResponse)
def toggle_api_resource(
    id: UUID,
    db: Session = Depends(get_db)
) -> ApiResourceResponse:
    """
    Toggle API resource active status (active ↔ inactive).
    Updates dynamic routes accordingly.
    """
    api_resource = db.query(ApiResource).filter(ApiResource.id == id).first()
    if not api_resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API resource with id {id} not found",
        )

    # Toggle is_active
    api_resource.is_active = not api_resource.is_active

    db.commit()
    db.refresh(api_resource)

    # Convert to response format with camelCase
    resource_dict = {
        "id": api_resource.id,
        "path": api_resource.path,
        "method": api_resource.method,
        "description": api_resource.description,
        "isActive": api_resource.is_active,
        "businessObjectId": api_resource.business_object_id,
        "businessObjectName": api_resource.business_object_name,
        "businessObjectParams": convert_params_to_camel_case(api_resource.business_object_params),
        "executionChain": convert_execution_chain_to_camel_case(api_resource.execution_chain),
        "createdAt": api_resource.created_at,
        "updatedAt": api_resource.updated_at,
    }

    return ApiResourceResponse(**resource_dict)


@router.post("/execute", status_code=status.HTTP_200_OK)
async def execute_resource(
    request: ExecuteResourceRequest = Body(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generic endpoint to execute any API resource.

    This endpoint accepts:
    - resource_id: UUID of the API resource to execute
    - connection_id: Database connection ID (UUID) or slug (string)
    - parameters: Dictionary with resource-specific parameters

    Returns the execution result (rows for SELECT, rowCount for DML, or chain results).

    Example request:
    {
        "resource_id": "abc-123-def",
        "connection_id": "my-postgres-db",
        "parameters": {
            "param1": "value1",
            "param2": 123
        }
    }
    """
    # Import here to avoid circular dependency
    from app.core.dynamic_routes import execute_dynamic_endpoint_logic

    # Fetch API resource
    print(id)
    api_resource = db.query(ApiResource).filter(ApiResource.id == request.resource_id).first()
    print(api_resource)
    if not api_resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API resource with id {request.resource_id} not found"
        )

    # Validate it's active
    if not api_resource.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API resource is not active"
        )

    # Execute resource using existing logic
    result = await execute_dynamic_endpoint_logic(
        api_resource=api_resource,
        connection_id=request.connection_id,
        parameters=request.parameters,
        db=db
    )

    return result
