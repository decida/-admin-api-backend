"""
Thread-safe SQLAlchemy engine pool manager with TTL-based caching.

This module provides a singleton manager for caching SQLAlchemy engines
to avoid expensive engine creation on every request. Engines are cached
in-memory with a 30-minute TTL and properly disposed when evicted.

Key Features:
- In-memory caching with threading.Lock synchronization
- TTL-based expiration (default: 30 minutes)
- Lazy engine creation on first access
- Automatic disposal on cache eviction
- Per-database UUID-based cache keys
- Manual invalidation for database updates/deletes
- Background cleanup thread (optional)
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
from uuid import UUID

from sqlalchemy import create_engine, Engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)


class CachedEngine:
    """Wrapper for a cached SQLAlchemy engine with TTL tracking."""

    def __init__(self, engine: Engine, ttl_seconds: int):
        """
        Initialize cached engine wrapper.

        Args:
            engine: SQLAlchemy Engine instance
            ttl_seconds: Time-to-live in seconds
        """
        self.engine = engine
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0

    def is_expired(self) -> bool:
        """Check if the engine has exceeded its TTL."""
        age = datetime.utcnow() - self.last_accessed
        return age.total_seconds() > self.ttl_seconds

    def mark_accessed(self) -> None:
        """Update last accessed timestamp and increment counter."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


class EnginePoolManager:
    """
    Thread-safe singleton manager for SQLAlchemy engine pooling.

    Features:
    - In-memory caching with threading.Lock synchronization
    - TTL-based expiration (default: 30 minutes)
    - Lazy engine creation on first access
    - Automatic disposal on cache eviction
    - Per-database UUID-based cache keys
    - Manual invalidation for database updates/deletes

    Thread Safety:
    - Global lock (_lock) protects cache structure operations
    - Per-engine locks prevent concurrent creation of same engine
    - Double-checked locking pattern for optimal performance
    """

    _instance: Optional["EnginePoolManager"] = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the engine pool manager."""
        # Only initialize once
        if hasattr(self, "_initialized"):
            return

        self._cache: Dict[str, CachedEngine] = {}
        self._lock = threading.Lock()  # Protects cache structure
        self._creation_locks: Dict[str, threading.Lock] = {}  # Per-engine creation locks
        self._cleanup_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._initialized = True

        logger.info(
            f"EnginePoolManager initialized with TTL={settings.ENGINE_POOL_TTL}s, "
            f"pool_size={settings.ENGINE_POOL_SIZE}, max_overflow={settings.ENGINE_POOL_MAX_OVERFLOW}"
        )

    def _get_creation_lock(self, cache_key: str) -> threading.Lock:
        """Get or create a lock for specific cache key."""
        with self._lock:
            if cache_key not in self._creation_locks:
                self._creation_locks[cache_key] = threading.Lock()
            return self._creation_locks[cache_key]

    def get_engine(
        self,
        database_id: UUID,
        connection_string: str,
        use_null_pool: bool = False,
    ) -> Engine:
        """
        Get or create a cached SQLAlchemy engine.

        Args:
            database_id: UUID of the database (cache key)
            connection_string: Database connection string
            use_null_pool: If True, use NullPool (for special T-SQL blocks)

        Returns:
            SQLAlchemy Engine instance

        Thread Safety:
            Uses double-checked locking pattern:
            1. Check cache without lock (fast path)
            2. Acquire per-engine creation lock
            3. Check cache again (someone might have created it)
            4. Create engine if still missing
        """
        cache_key = str(database_id)

        # Fast path: Check if engine exists and is valid (no lock)
        with self._lock:
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                if not cached.is_expired():
                    cached.mark_accessed()
                    logger.debug(
                        f"Engine cache HIT for database {database_id} "
                        f"(access #{cached.access_count}, age: {(datetime.utcnow() - cached.created_at).total_seconds():.1f}s)"
                    )
                    return cached.engine
                else:
                    # Expired - will be recreated
                    logger.info(
                        f"Engine cache EXPIRED for database {database_id}, disposing and recreating"
                    )
                    self._dispose_engine(cache_key)

        # Slow path: Create engine with per-key lock
        creation_lock = self._get_creation_lock(cache_key)

        with creation_lock:
            # Double-check: another thread might have created it
            with self._lock:
                if cache_key in self._cache:
                    cached = self._cache[cache_key]
                    if not cached.is_expired():
                        cached.mark_accessed()
                        logger.debug(
                            f"Engine cache HIT after lock wait for database {database_id}"
                        )
                        return cached.engine

            # Create new engine
            logger.info(
                f"Engine cache MISS for database {database_id}, creating new engine"
            )

            try:
                if use_null_pool:
                    # Special case for T-SQL blocks with multiple result sets
                    engine = create_engine(
                        connection_string, poolclass=NullPool, isolation_level="AUTOCOMMIT"
                    )
                    logger.info(f"Created NullPool engine for database {database_id}")
                else:
                    # Standard pooled engine
                    engine = create_engine(
                        connection_string,
                        pool_pre_ping=settings.ENGINE_POOL_PRE_PING,
                        pool_size=settings.ENGINE_POOL_SIZE,
                        max_overflow=settings.ENGINE_POOL_MAX_OVERFLOW,
                    )
                    logger.info(
                        f"Created pooled engine for database {database_id} "
                        f"(pool_size={settings.ENGINE_POOL_SIZE}, max_overflow={settings.ENGINE_POOL_MAX_OVERFLOW})"
                    )

                # Cache the engine
                cached = CachedEngine(engine, settings.ENGINE_POOL_TTL)

                with self._lock:
                    self._cache[cache_key] = cached

                return engine

            except Exception as e:
                logger.error(f"Failed to create engine for database {database_id}: {e}")
                raise

    def _dispose_engine(self, cache_key: str) -> None:
        """
        Dispose an engine and remove from cache.

        MUST be called with self._lock held!
        """
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            try:
                cached.engine.dispose()
                logger.info(
                    f"Disposed engine for {cache_key} "
                    f"(lifetime: {(datetime.utcnow() - cached.created_at).total_seconds():.1f}s, "
                    f"access_count: {cached.access_count})"
                )
            except Exception as e:
                logger.warning(f"Error disposing engine for {cache_key}: {e}")
            finally:
                del self._cache[cache_key]
                # Clean up creation lock if no one is using it
                if cache_key in self._creation_locks:
                    del self._creation_locks[cache_key]

    def invalidate(self, database_id: UUID) -> None:
        """
        Manually invalidate (dispose and remove) an engine from cache.

        Args:
            database_id: UUID of the database to invalidate

        Use Cases:
            - Database connection string updated
            - Database deleted
            - Connection test failed
        """
        cache_key = str(database_id)

        with self._lock:
            if cache_key in self._cache:
                logger.info(f"Manually invalidating engine for database {database_id}")
                self._dispose_engine(cache_key)
            else:
                logger.debug(
                    f"No cached engine to invalidate for database {database_id}"
                )

    def cleanup_expired(self) -> int:
        """
        Clean up expired engines from cache.

        Returns:
            Number of engines disposed

        Note:
            Called periodically by background thread or can be called manually
        """
        expired_keys = []

        with self._lock:
            for cache_key, cached in list(self._cache.items()):
                if cached.is_expired():
                    expired_keys.append(cache_key)

        # Dispose outside the iteration to avoid modification during iteration
        count = 0
        for cache_key in expired_keys:
            with self._lock:
                # Double-check it's still expired (might have been accessed)
                if cache_key in self._cache and self._cache[cache_key].is_expired():
                    self._dispose_engine(cache_key)
                    count += 1

        if count > 0:
            logger.info(f"Cleaned up {count} expired engine(s)")

        return count

    def start_cleanup_thread(self) -> None:
        """
        Start background thread for periodic cleanup of expired engines.

        Optional: Can rely on lazy cleanup instead if preferred.
        """
        if self._cleanup_thread is not None:
            logger.warning("Cleanup thread already running")
            return

        def cleanup_worker():
            logger.info(
                f"Engine pool cleanup thread started "
                f"(interval: {settings.ENGINE_POOL_CLEANUP_INTERVAL}s)"
            )

            while not self._shutdown_event.wait(
                timeout=settings.ENGINE_POOL_CLEANUP_INTERVAL
            ):
                try:
                    self.cleanup_expired()
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {e}")

            logger.info("Engine pool cleanup thread stopped")

        self._cleanup_thread = threading.Thread(
            target=cleanup_worker, name="EnginePoolCleanup", daemon=True
        )
        self._cleanup_thread.start()

    def stop_cleanup_thread(self) -> None:
        """Stop the background cleanup thread."""
        if self._cleanup_thread is not None:
            logger.info("Stopping cleanup thread...")
            self._shutdown_event.set()
            self._cleanup_thread.join(timeout=5)
            self._cleanup_thread = None
            self._shutdown_event.clear()

    def dispose_all(self) -> None:
        """
        Dispose all cached engines and clear the cache.

        Called on application shutdown.
        """
        logger.info("Disposing all cached engines...")

        with self._lock:
            count = len(self._cache)
            for cache_key in list(self._cache.keys()):
                self._dispose_engine(cache_key)

        logger.info(f"Disposed {count} engine(s)")

    def get_stats(self) -> dict:
        """
        Get current cache statistics.

        Returns:
            Dictionary with cache stats (for monitoring/debugging)
        """
        with self._lock:
            stats = {"total_engines": len(self._cache), "engines": []}

            for cache_key, cached in self._cache.items():
                age = (datetime.utcnow() - cached.created_at).total_seconds()
                idle = (datetime.utcnow() - cached.last_accessed).total_seconds()

                stats["engines"].append(
                    {
                        "database_id": cache_key,
                        "age_seconds": age,
                        "idle_seconds": idle,
                        "access_count": cached.access_count,
                        "is_expired": cached.is_expired(),
                    }
                )

        return stats


# Global singleton instance
_engine_pool_manager: Optional[EnginePoolManager] = None


def get_engine_pool() -> EnginePoolManager:
    """
    Get the global engine pool manager singleton.

    Returns:
        EnginePoolManager instance
    """
    global _engine_pool_manager

    if _engine_pool_manager is None:
        _engine_pool_manager = EnginePoolManager()

    return _engine_pool_manager
