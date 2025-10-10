from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.business_object import CommandType


class BusinessObjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the business object for search")
    command_type: CommandType = Field(..., description="Type of SQL command (select, insert, update, delete)")
    sql_command: str = Field(..., description="SQL command encoded in BASE64")
    tags: list[str] = Field(default_factory=list, description="Array of strings with tags for filters")

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
