from datetime import datetime
from uuid import uuid4
import enum

from sqlalchemy import String, DateTime, Text, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CommandType(str, enum.Enum):
    select = "select"
    insert = "insert"
    update = "update"
    delete = "delete"


class BusinessObject(Base):
    __tablename__ = "business_objects"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    command_type: Mapped[CommandType] = mapped_column(
        SQLEnum(CommandType, name="command_type"),
        nullable=False,
    )
    sql_command: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    params: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<BusinessObject(id={self.id}, name={self.name}, command_type={self.command_type})>"
