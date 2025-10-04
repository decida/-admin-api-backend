from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, DateTime, Text, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.db.base import Base


class DatabaseStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Database(Base):
    __tablename__ = "databases"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    connection_string: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[DatabaseStatus] = mapped_column(
        SQLEnum(DatabaseStatus, name="database_status"),
        default=DatabaseStatus.active,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Database(id={self.id}, name={self.name}, type={self.type})>"