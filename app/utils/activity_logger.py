"""
Activity Logger Utility
Helper functions to easily log activities throughout the application.
"""
from typing import Optional, Any
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.activity import Activity, ActivityIcon, ActivityColor


def log_activity(
    db: Session,
    action: str,
    item: str,
    icon: ActivityIcon = ActivityIcon.info,
    color: ActivityColor = ActivityColor.blue,
    user_email: Optional[str] = None,
    user_id: Optional[UUID] = None,
    extra_data: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Activity:
    """
    Log an activity to the database.

    Args:
        db: Database session
        action: Description of the action
        item: Item affected by the action
        icon: Icon for UI display
        color: Color theme for UI
        user_email: Email of user who performed action
        user_id: UUID of authenticated user
        extra_data: Additional JSON data
        ip_address: IP address of request
        user_agent: User agent string

    Returns:
        Created Activity object

    Example:
        log_activity(
            db=db,
            action="Created database connection",
            item="Production DB",
            icon=ActivityIcon.database,
            color=ActivityColor.blue,
            user_email="user@example.com",
            extra_data={"database_type": "sqlserver"}
        )
    """
    activity = Activity(
        action=action,
        item=item,
        icon=icon,
        color=color,
        user_email=user_email,
        user_id=user_id,
        extra_data=extra_data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


# Convenience functions for common activities

def log_database_created(
    db: Session,
    database_name: str,
    user_email: Optional[str] = None,
    extra_data: Optional[dict] = None
) -> Activity:
    """Log database creation activity."""
    return log_activity(
        db=db,
        action="Created database connection",
        item=database_name,
        icon=ActivityIcon.database,
        color=ActivityColor.blue,
        user_email=user_email,
        extra_data=extra_data,
    )


def log_database_updated(
    db: Session,
    database_name: str,
    user_email: Optional[str] = None,
    extra_data: Optional[dict] = None
) -> Activity:
    """Log database update activity."""
    return log_activity(
        db=db,
        action="Updated database connection",
        item=database_name,
        icon=ActivityIcon.edit,
        color=ActivityColor.green,
        user_email=user_email,
        extra_data=extra_data,
    )


def log_database_deleted(
    db: Session,
    database_name: str,
    user_email: Optional[str] = None,
    extra_data: Optional[dict] = None
) -> Activity:
    """Log database deletion activity."""
    return log_activity(
        db=db,
        action="Deleted database connection",
        item=database_name,
        icon=ActivityIcon.delete,
        color=ActivityColor.red,
        user_email=user_email,
        extra_data=extra_data,
    )


def log_backup_created(
    db: Session,
    backup_size_mb: float,
    total_records: int,
    user_email: Optional[str] = None
) -> Activity:
    """Log backup creation activity."""
    return log_activity(
        db=db,
        action="Created backup",
        item=f"{total_records} database connections",
        icon=ActivityIcon.download,
        color=ActivityColor.purple,
        user_email=user_email,
        extra_data={"size_mb": backup_size_mb, "total_records": total_records},
    )


def log_error(
    db: Session,
    error_message: str,
    item: str,
    user_email: Optional[str] = None,
    extra_data: Optional[dict] = None
) -> Activity:
    """Log error activity."""
    return log_activity(
        db=db,
        action=error_message,
        item=item,
        icon=ActivityIcon.error,
        color=ActivityColor.red,
        user_email=user_email,
        extra_data=extra_data,
    )


def log_warning(
    db: Session,
    warning_message: str,
    item: str,
    user_email: Optional[str] = None,
    extra_data: Optional[dict] = None
) -> Activity:
    """Log warning activity."""
    return log_activity(
        db=db,
        action=warning_message,
        item=item,
        icon=ActivityIcon.warning,
        color=ActivityColor.yellow,
        user_email=user_email,
        extra_data=extra_data,
    )
