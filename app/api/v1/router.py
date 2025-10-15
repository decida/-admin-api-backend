from fastapi import APIRouter

from app.api.v1.endpoints import databases, activities, business_objects, api_resources

api_router = APIRouter()

api_router.include_router(databases.router, prefix="/databases", tags=["databases"])
api_router.include_router(activities.router, prefix="/activities", tags=["activities"])
api_router.include_router(business_objects.router, prefix="/business-objects", tags=["business-objects"])
api_router.include_router(api_resources.router, prefix="/api-resources", tags=["api-resources"])