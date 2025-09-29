from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.models.database import DatabaseStatus


class DatabaseBase(BaseModel):
    name: str
    type: str
    connection_string: str
    description: str | None = None
    status: DatabaseStatus = DatabaseStatus.active


class DatabaseCreate(DatabaseBase):
    pass


class DatabaseUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    connection_string: str | None = None
    description: str | None = None
    status: DatabaseStatus | None = None


class DatabaseInDB(DatabaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class DatabaseResponse(DatabaseInDB):
    pass