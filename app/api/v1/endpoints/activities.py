from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.activity import Activity
from app.schemas.activity import (
    ActivityCreate,
    ActivityResponse,
    ActivityListResponse,
    ActivityStats,
    ActivityUpdate,
)

router = APIRouter()


@router.get("/", response_model=ActivityListResponse)
async def get_activities(
    skip: int = 0,
    limit: int = 50,
    user_email: str | None = None,
    action: str | None = None,
    db: Session = Depends(get_db)
) -> ActivityListResponse:
    """
    Get paginated list of activities.

    Query parameters:
    - skip: Number of records to skip (default: 0)
    - limit: Max records to return (default: 50, max: 100)
    - user_email: Filter by user email
    - action: Filter by action (partial match)
    """
    # Build query
    query = db.query(Activity)

    if user_email:
        query = query.filter(Activity.user_email == user_email)

    if action:
        query = query.filter(Activity.action.ilike(f"%{action}%"))

    # Get total count
    total = query.count()

    # Get paginated results
    activities = query.order_by(desc(Activity.timestamp)).offset(skip).limit(min(limit, 100)).all()

    return ActivityListResponse(
        activities=[ActivityResponse.model_validate(a) for a in activities],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total
    )


@router.get("/stats", response_model=ActivityStats)
async def get_activity_stats(db: Session = Depends(get_db)) -> ActivityStats:
    """Get activity statistics."""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    total = db.query(Activity).count()
    today = db.query(Activity).filter(Activity.timestamp >= today_start).count()
    this_week = db.query(Activity).filter(Activity.timestamp >= week_start).count()
    this_month = db.query(Activity).filter(Activity.timestamp >= month_start).count()

    # Most active user
    most_active = db.query(
        Activity.user_email,
        func.count(Activity.id).label('count')
    ).filter(
        Activity.user_email.isnot(None)
    ).group_by(
        Activity.user_email
    ).order_by(
        desc('count')
    ).first()

    # Most common action
    most_common = db.query(
        Activity.action,
        func.count(Activity.id).label('count')
    ).group_by(
        Activity.action
    ).order_by(
        desc('count')
    ).first()

    return ActivityStats(
        total_activities=total,
        activities_today=today,
        activities_this_week=this_week,
        activities_this_month=this_month,
        most_active_user=most_active[0] if most_active else None,
        most_common_action=most_common[0] if most_common else None,
    )


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(activity_id: int, db: Session = Depends(get_db)) -> ActivityResponse:
    """Get activity by ID."""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {activity_id} not found"
        )
    return ActivityResponse.model_validate(activity)


@router.post("/", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    activity_in: ActivityCreate,
    request: Request,
    db: Session = Depends(get_db)
) -> ActivityResponse:
    """
    Create new activity log entry.

    Automatically captures IP address and User-Agent from request headers.
    """
    # Auto-capture IP and User-Agent if not provided
    activity_data = activity_in.model_dump()

    if not activity_data.get("ip_address"):
        # Try to get real IP from headers (considering proxies)
        activity_data["ip_address"] = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
            request.headers.get("X-Real-IP") or
            request.client.host if request.client else None
        )

    if not activity_data.get("user_agent"):
        activity_data["user_agent"] = request.headers.get("User-Agent")

    activity = Activity(**activity_data)
    db.add(activity)
    db.commit()
    db.refresh(activity)

    return ActivityResponse.model_validate(activity)


@router.patch("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: int,
    activity_in: ActivityUpdate,
    db: Session = Depends(get_db)
) -> ActivityResponse:
    """Update activity metadata (limited fields)."""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {activity_id} not found"
        )

    update_data = activity_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(activity, field, value)

    db.commit()
    db.refresh(activity)

    return ActivityResponse.model_validate(activity)


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(activity_id: int, db: Session = Depends(get_db)) -> None:
    """Delete activity by ID."""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {activity_id} not found"
        )

    db.delete(activity)
    db.commit()


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_old_activities(
    days: int = 90,
    db: Session = Depends(get_db)
) -> None:
    """
    Delete activities older than specified days.

    Default: 90 days (3 months)
    Useful for cleanup and GDPR compliance.
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    deleted_count = db.query(Activity).filter(Activity.timestamp < cutoff_date).delete()
    db.commit()

    return {"message": f"Deleted {deleted_count} activities older than {days} days"}
