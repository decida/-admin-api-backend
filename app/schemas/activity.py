from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any

from app.models.activity import ActivityIcon, ActivityColor


class ActivityBase(BaseModel):
    """Base schema for Activity."""
    action: str = Field(..., max_length=255, description="Action performed")
    item: str = Field(..., max_length=500, description="Item affected by action")
    icon: ActivityIcon = Field(default=ActivityIcon.info, description="Icon for UI")
    color: ActivityColor = Field(default=ActivityColor.blue, description="Color theme for UI")
    user_email: Optional[str] = Field(None, max_length=255, description="Email of user who performed action")
    user_id: Optional[UUID] = Field(None, description="UUID of authenticated user")
    extra_data: Optional[dict[str, Any]] = Field(None, description="Additional JSON data")


class ActivityCreate(ActivityBase):
    """Schema for creating activity."""
    ip_address: Optional[str] = Field(None, description="IP address of request")
    user_agent: Optional[str] = Field(None, description="User agent string")


class ActivityUpdate(BaseModel):
    """Schema for updating activity (limited fields)."""
    extra_data: Optional[dict[str, Any]] = None


class ActivityInDB(ActivityBase):
    """Schema for activity in database."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime | str
    created_at: datetime | str


class ActivityResponse(ActivityInDB):
    """Schema for activity API response."""
    pass


class ActivityListResponse(BaseModel):
    """Schema for paginated activity list."""
    activities: list[ActivityResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class ActivityStats(BaseModel):
    """Statistics about activities."""
    total_activities: int
    activities_today: int
    activities_this_week: int
    activities_this_month: int
    most_active_user: Optional[str] = None
    most_common_action: Optional[str] = None
