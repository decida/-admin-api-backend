from fastapi import APIRouter

from app.api.v1.endpoints import databases, activities

api_router = APIRouter()

api_router.include_router(databases.router, prefix="/databases", tags=["databases"])
api_router.include_router(activities.router, prefix="/activities", tags=["activities"])