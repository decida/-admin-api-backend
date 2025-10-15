import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.cache import close_redis
from app.core.dynamic_routes import dynamic_router, refresh_dynamic_routes
from app.db.session import SessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")

    # Initialize dynamic routes from database
    try:
        db = SessionLocal()
        try:
            refresh_dynamic_routes(db)
            logger.info("Dynamic routes initialized successfully")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to initialize dynamic routes: {e}")

    yield

    # Shutdown
    await close_redis()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Include dynamic routes router (no prefix - routes define their own paths)
app.include_router(dynamic_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}