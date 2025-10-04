from datetime import datetime
import enum
from sqlalchemy import String, DateTime, Text, Enum as SQLEnum, BigInteger, func
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActivityIcon(str, enum.Enum):
    """Icons for activity display."""
    database = "database"
    edit = "edit"
    delete = "delete"
    add = "add"
    plus = "plus"
    minus = "minus"
    user = "user"
    settings = "settings"
    upload = "upload"
    download = "download"
    sync = "sync"
    refresh = "refresh"
    search = "search"
    filter = "filter"
    save = "save"
    copy = "copy"
    paste = "paste"
    cut = "cut"
    file = "file"
    folder = "folder"
    lock = "lock"
    unlock = "unlock"
    key = "key"
    shield = "shield"
    bell = "bell"
    mail = "mail"
    phone = "phone"
    calendar = "calendar"
    clock = "clock"
    chart = "chart"
    graph = "graph"
    warning = "warning"
    error = "error"
    success = "success"
    info = "info"
    question = "question"
    check = "check"
    close = "close"
    menu = "menu"
    more = "more"
    link = "link"
    external = "external"
    home = "home"
    star = "star"
    heart = "heart"
    eye = "eye"
    eye_off = "eye_off"
    trash = "trash"
    archive = "archive"
    pin = "pin"
    flag = "flag"
    tag = "tag"
    bookmark = "bookmark"
    wifi = "wifi"
    wifi_off = "wifi_off"
    network = "network"
    server = "server"
    cloud = "cloud"
    cloud_upload = "cloud_upload"
    cloud_download = "cloud_download"


class ActivityColor(str, enum.Enum):
    """Color themes for activity display."""
    blue = "blue"
    green = "green"
    red = "red"
    yellow = "yellow"
    purple = "purple"
    orange = "orange"
    gray = "gray"
    indigo = "indigo"
    pink = "pink"


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    item: Mapped[str] = mapped_column(String(500), nullable=False)
    icon: Mapped[ActivityIcon] = mapped_column(
        SQLEnum(ActivityIcon, name="activity_icon"),
        default=ActivityIcon.info,
        nullable=False,
    )
    color: Mapped[ActivityColor] = mapped_column(
        SQLEnum(ActivityColor, name="activity_color"),
        default=ActivityColor.blue,
        nullable=False,
    )
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Activity(id={self.id}, action={self.action}, item={self.item})>"
