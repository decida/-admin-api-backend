from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BusinessObjectParam(BaseModel):
    """Schema for Business Object parameter definition."""
    name: str
    type: str
    required: bool = False
    default_value: Any = Field(None, alias='defaultValue')

    model_config = ConfigDict(populate_by_name=True)


class ApiResourceBase(BaseModel):
    """Base schema for API Resource."""
    path: str = Field(..., min_length=1, max_length=500, description="API endpoint path (e.g., /api/v1/consultar-paciente)")
    description: str | None = Field(None, max_length=1000, description="Resource description")
    is_active: bool = Field(True, alias='isActive', description="Whether the resource is active")
    business_object_id: UUID = Field(..., alias='businessObjectId', description="Business Object ID to execute")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Ensure path starts with /"""
        if not v.startswith('/'):
            raise ValueError('Path must start with /')
        return v


class ApiResourceCreate(ApiResourceBase):
    """Schema for creating an API Resource."""
    pass


class ApiResourceUpdate(BaseModel):
    """Schema for updating an API Resource."""
    path: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, max_length=1000)
    is_active: bool | None = Field(None, alias='isActive')
    business_object_id: UUID | None = Field(None, alias='businessObjectId')

    model_config = ConfigDict(populate_by_name=True)

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str | None) -> str | None:
        """Ensure path starts with / if provided"""
        if v is not None and not v.startswith('/'):
            raise ValueError('Path must start with /')
        return v


class ApiResourceResponse(BaseModel):
    """Schema for API Resource response."""
    id: UUID
    path: str
    method: str
    description: str | None
    is_active: bool = Field(alias='isActive')
    business_object_id: UUID = Field(alias='businessObjectId')
    business_object_name: str = Field(alias='businessObjectName')
    business_object_params: list[BusinessObjectParam] = Field(alias='businessObjectParams')
    created_at: datetime = Field(alias='createdAt')
    updated_at: datetime = Field(alias='updatedAt')

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ApiResourceExecuteRequest(BaseModel):
    """Schema for executing a dynamic API resource."""
    # Accept any key-value pairs as parameters
    model_config = ConfigDict(extra='allow')


class ApiResourceExecuteResponse(BaseModel):
    """Schema for dynamic API resource execution response."""
    success: bool
    rows: list[dict] | None = None
    row_count: int | None = Field(None, alias="rowCount")
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True)
