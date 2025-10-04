import json
import logging
from typing import Optional, Any
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis client instance
redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
            )
            # Test connection
            await redis_client.ping()
            logger.info(f"Redis connected to {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}: {e}")
            raise
    return redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def get_cache(key: str) -> Optional[Any]:
    """
    Get value from cache.
    Returns None if key doesn't exist or cache is unavailable.
    """
    try:
        client = await get_redis()
        value = await client.get(key)
        if value:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(value)
        logger.debug(f"Cache MISS: {key}")
        return None
    except Exception as e:
        # Log error but don't fail the request
        logger.warning(f"Cache get error for key '{key}': {e}")
        return None


async def set_cache(key: str, value: Any, ttl: int = settings.CACHE_TTL) -> bool:
    """
    Set value in cache with TTL (time to live in seconds).
    Returns True if successful, False otherwise.
    """
    try:
        client = await get_redis()
        serialized = json.dumps(value)
        await client.setex(key, ttl, serialized)
        logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
        return True
    except Exception as e:
        # Log error but don't fail the request
        logger.warning(f"Cache set error for key '{key}': {e}")
        return False


async def delete_cache(key: str) -> bool:
    """
    Delete key from cache.
    Returns True if successful, False otherwise.
    """
    try:
        client = await get_redis()
        await client.delete(key)
        logger.debug(f"Cache DELETE: {key}")
        return True
    except Exception as e:
        logger.warning(f"Cache delete error for key '{key}': {e}")
        return False


async def delete_pattern(pattern: str) -> bool:
    """
    Delete all keys matching pattern.
    Pattern example: "databases:*"
    Returns True if successful, False otherwise.
    """
    try:
        client = await get_redis()
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
            logger.info(f"Cache invalidated: {len(keys)} keys matching '{pattern}'")
        return True
    except Exception as e:
        logger.warning(f"Cache delete pattern error for '{pattern}': {e}")
        return False


def cache_key_database_list(skip: int = 0, limit: int = 100) -> str:
    """Generate cache key for database list."""
    return f"databases:list:{skip}:{limit}"


def cache_key_database(id_or_slug: str) -> str:
    """Generate cache key for single database."""
    return f"databases:item:{id_or_slug}"


async def invalidate_database_cache() -> None:
    """Invalidate all database-related cache entries."""
    await delete_pattern("databases:*")


# TTL constants for different data types
CACHE_TTL_SHORT = 300      # 5 minutes - frequently changing data
CACHE_TTL_MEDIUM = 1800    # 30 minutes - moderate changes
CACHE_TTL_LONG = 43200     # 12 hours - rarely changing data
CACHE_TTL_STATIC = 86400   # 24 hours - almost static data
