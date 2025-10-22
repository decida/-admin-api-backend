from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ApiResource(Base):
    __tablename__ = "api_resources"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, index=True
    )
    path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    method: Mapped[str] = mapped_column(String(10), default="POST", nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relacionamento com Business Object
    business_object_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_objects.id", ondelete="RESTRICT"),
        nullable=False
    )
    business_object: Mapped["BusinessObject"] = relationship("BusinessObject", back_populates="api_resources")

    # Metadata do Business Object (snapshot no momento da criação)
    business_object_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_object_params: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Execution chain for sequential business object execution
    execution_chain: Mapped[list | None] = mapped_column(JSONB, default=None, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ApiResource(id={self.id}, path={self.path}, method={self.method}, active={self.is_active})>"
