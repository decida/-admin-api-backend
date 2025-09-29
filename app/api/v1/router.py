from fastapi import APIRouter

from app.api.v1.endpoints import databases

api_router = APIRouter()

api_router.include_router(databases.router, prefix="/databases", tags=["databases"])