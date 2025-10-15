from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.api_resource import ApiResource
from app.models.business_object import BusinessObject
from app.schemas.api_resource import (
    ApiResourceCreate,
    ApiResourceResponse,
    ApiResourceUpdate,
)
from app.utils.parameter_validation import convert_from_dict

router = APIRouter()


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

    # Create API resource with snapshot of Business Object metadata
    api_resource = ApiResource(
        path=api_resource_in.path,
        method="POST",  # Always POST for now
        description=api_resource_in.description,
        is_active=api_resource_in.is_active,
        business_object_id=api_resource_in.business_object_id,
        business_object_name=business_object.name,
        business_object_params=business_object.params,
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
        "createdAt": api_resource.created_at,
        "updatedAt": api_resource.updated_at,
    }

    # Trigger dynamic route refresh (will be implemented later)
    try:
        from app.core.dynamic_routes import refresh_dynamic_routes
        refresh_dynamic_routes(db)
    except ImportError:
        pass  # Dynamic routes not yet implemented

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
    update_data = api_resource_in.model_dump(exclude_unset=True, exclude={'business_object_id'})
    for field, value in update_data.items():
        # Convert camelCase to snake_case
        if field == 'isActive':
            setattr(api_resource, 'is_active', value)
        else:
            setattr(api_resource, field, value)

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
        "createdAt": api_resource.created_at,
        "updatedAt": api_resource.updated_at,
    }

    # Trigger dynamic route refresh
    try:
        from app.core.dynamic_routes import refresh_dynamic_routes
        refresh_dynamic_routes(db)
    except ImportError:
        pass

    return ApiResourceResponse(**resource_dict)


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

    # Trigger dynamic route refresh
    try:
        from app.core.dynamic_routes import refresh_dynamic_routes
        refresh_dynamic_routes(db)
    except ImportError:
        pass


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
        "createdAt": api_resource.created_at,
        "updatedAt": api_resource.updated_at,
    }

    # Trigger dynamic route refresh
    try:
        from app.core.dynamic_routes import refresh_dynamic_routes
        refresh_dynamic_routes(db)
    except ImportError:
        pass

    return ApiResourceResponse(**resource_dict)
