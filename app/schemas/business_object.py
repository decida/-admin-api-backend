from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.business_object import CommandType


class SqlParameter(BaseModel):
    """Schema for SQL parameter definition."""
    name: str = Field(..., min_length=1, description="Parameter name (without colon)")
    type: Literal["string", "number", "date"] = Field(..., description="Parameter type")
    required: bool = Field(default=True, description="Whether parameter is required")
    defaultValue: Any = Field(default=None, description="Default value for the parameter", alias="defaultValue")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure parameter name is valid (alphanumeric and underscore only)."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Parameter name must contain only alphanumeric characters, underscores, and hyphens')
        if v.startswith(':'):
            raise ValueError('Parameter name should not include the colon prefix')
        return v

    @field_validator('defaultValue')
    @classmethod
    def validate_default_value(cls, v: Any, info) -> Any:
        """Validate default value matches parameter type."""
        if v is None:
            return v

        # Access the type field from the data being validated
        param_type = info.data.get('type')

        if param_type == 'number':
            if not isinstance(v, (int, float)):
                try:
                    float(v)
                except (ValueError, TypeError):
                    raise ValueError(f'defaultValue must be a number for type "number"')
        elif param_type == 'date':
            if not isinstance(v, str):
                raise ValueError(f'defaultValue must be a string (ISO date format) for type "date"')
        elif param_type == 'string':
            if not isinstance(v, str):
                raise ValueError(f'defaultValue must be a string for type "string"')

        return v


class BusinessObjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the business object for search")
    command_type: CommandType = Field(..., description="Type of SQL command (select, insert, update, delete)")
    sql_command: str = Field(..., description="SQL command encoded in BASE64")
    tags: list[str] = Field(default_factory=list, description="Array of strings with tags for filters")
    params: list[SqlParameter] = Field(default_factory=list, description="Array of parameter definitions")

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Ensure tags is a list of strings."""
        if not isinstance(v, list):
            raise ValueError('tags must be a list')
        if not all(isinstance(tag, str) for tag in v):
            raise ValueError('all tags must be strings')
        return v


class BusinessObjectCreate(BusinessObjectBase):
    pass


class BusinessObjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    sql_command: str | None = None
    tags: list[str] | None = None
    params: list[SqlParameter] | None = None
    # Note: command_type is intentionally excluded - it's immutable after creation

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Ensure tags is a list of strings if provided."""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError('tags must be a list')
            if not all(isinstance(tag, str) for tag in v):
                raise ValueError('all tags must be strings')
        return v


class BusinessObjectInDB(BusinessObjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class BusinessObjectResponse(BusinessObjectInDB):
    pass


class BusinessObjectTestRequest(BaseModel):
    """Request schema for testing a business object execution."""
    connection_id: UUID = Field(..., description="UUID of the connection to use")
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Parameters to replace in SQL placeholders ({{parameter_name}})"
    )


class BusinessObjectTestResponse(BaseModel):
    """Response schema for business object test execution."""
    success: bool
    rows: list[dict] | None = None
    row_count: int | None = Field(None, alias="rowCount")
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class ExecuteSqlRequest(BaseModel):
    """Request schema for executing generic SQL commands."""
    connection_id: str = Field(..., description="UUID or slug of the connection to use")
    sql_command: str = Field(..., description="SQL command to execute (DML or DDL)")
