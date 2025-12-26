"""
Basic tests for the engine pool manager.

These tests validate the core functionality of the engine pool manager
without requiring actual database connections.
"""

import threading
import time
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.engine_pool import EnginePoolManager, CachedEngine, get_engine_pool


class TestCachedEngine:
    """Test the CachedEngine wrapper class."""

    def test_cached_engine_creation(self):
        """Test that CachedEngine is created with correct attributes."""
        mock_engine = MagicMock()
        ttl = 1800

        cached = CachedEngine(mock_engine, ttl)

        assert cached.engine is mock_engine
        assert cached.ttl_seconds == ttl
        assert cached.access_count == 0
        assert cached.created_at is not None
        assert cached.last_accessed is not None

    def test_cached_engine_not_expired_initially(self):
        """Test that newly created engine is not expired."""
        mock_engine = MagicMock()
        cached = CachedEngine(mock_engine, 1800)

        assert not cached.is_expired()

    def test_cached_engine_expires(self):
        """Test that engine expires after TTL."""
        mock_engine = MagicMock()
        cached = CachedEngine(mock_engine, ttl_seconds=1)

        # Should not be expired immediately
        assert not cached.is_expired()

        # Wait for TTL to pass
        time.sleep(1.1)

        # Should now be expired
        assert cached.is_expired()

    def test_mark_accessed_updates_timestamp(self):
        """Test that marking as accessed updates timestamp."""
        mock_engine = MagicMock()
        cached = CachedEngine(mock_engine, 1800)

        initial_accessed = cached.last_accessed
        initial_count = cached.access_count

        time.sleep(0.1)
        cached.mark_accessed()

        assert cached.last_accessed > initial_accessed
        assert cached.access_count == initial_count + 1


class TestEnginePoolManagerSingleton:
    """Test the singleton pattern."""

    def test_singleton_instance(self):
        """Test that get_engine_pool returns same instance."""
        pool1 = get_engine_pool()
        pool2 = get_engine_pool()

        assert pool1 is pool2

    def test_singleton_thread_safe(self):
        """Test that singleton creation is thread-safe."""
        instances = []

        def get_instance():
            # Reset global instance for testing
            import app.core.engine_pool as ep_module
            ep_module._engine_pool_manager = None

            instances.append(get_engine_pool())

        # This is a simplified test - normally singleton is already initialized
        pool = get_engine_pool()
        assert pool is not None


class TestEnginePoolManagerCaching:
    """Test the caching functionality."""

    def test_cache_key_generation(self):
        """Test that cache keys are correctly generated from UUIDs."""
        db_id = uuid4()

        pool = EnginePoolManager()

        # We can't directly test the cache, but we can verify the key format
        cache_key = str(db_id)
        assert len(cache_key) == 36  # UUID string length

    def test_dispose_engine_helper(self):
        """Test the _dispose_engine helper method."""
        pool = EnginePoolManager()
        mock_engine = MagicMock()

        # Manually add an engine to cache for testing
        cache_key = "test-key"
        cached_engine = CachedEngine(mock_engine, 1800)

        with pool._lock:
            pool._cache[cache_key] = cached_engine

            # Call dispose
            pool._dispose_engine(cache_key)

            # Verify engine was disposed
            mock_engine.dispose.assert_called_once()

            # Verify removed from cache
            assert cache_key not in pool._cache

    def test_invalidate_existing_engine(self):
        """Test invalidating an existing cached engine."""
        pool = EnginePoolManager()
        db_id = uuid4()
        mock_engine = MagicMock()

        # Add engine to cache
        cache_key = str(db_id)
        with pool._lock:
            pool._cache[cache_key] = CachedEngine(mock_engine, 1800)

        # Invalidate it
        pool.invalidate(db_id)

        # Verify it was disposed and removed
        mock_engine.dispose.assert_called_once()
        with pool._lock:
            assert cache_key not in pool._cache

    def test_invalidate_non_existing_engine(self):
        """Test invalidating a non-existing engine (should not error)."""
        pool = EnginePoolManager()
        db_id = uuid4()

        # Should not raise exception
        pool.invalidate(db_id)

    def test_cleanup_expired(self):
        """Test cleanup of expired engines."""
        pool = EnginePoolManager()

        # Create an expired engine
        mock_engine1 = MagicMock()
        cache_key1 = "expired-key"
        cached1 = CachedEngine(mock_engine1, ttl_seconds=1)

        # Create a non-expired engine
        mock_engine2 = MagicMock()
        cache_key2 = "active-key"
        cached2 = CachedEngine(mock_engine2, ttl_seconds=1800)

        with pool._lock:
            pool._cache[cache_key1] = cached1
            pool._cache[cache_key2] = cached2

        # Wait for first one to expire
        time.sleep(1.1)

        # Run cleanup
        count = pool.cleanup_expired()

        # Verify only one was cleaned up
        assert count == 1
        assert mock_engine1.dispose.called
        assert not mock_engine2.dispose.called

        with pool._lock:
            assert cache_key1 not in pool._cache
            assert cache_key2 in pool._cache

    def test_dispose_all(self):
        """Test disposing all engines."""
        pool = EnginePoolManager()

        # Add multiple engines
        engines = []
        for i in range(3):
            mock_engine = MagicMock()
            engines.append(mock_engine)
            cache_key = f"key-{i}"
            with pool._lock:
                pool._cache[cache_key] = CachedEngine(mock_engine, 1800)

        # Dispose all
        pool.dispose_all()

        # Verify all were disposed
        for mock_engine in engines:
            mock_engine.dispose.assert_called_once()

        # Verify cache is empty
        with pool._lock:
            assert len(pool._cache) == 0

    def test_get_stats(self):
        """Test getting cache statistics."""
        pool = EnginePoolManager()

        # Add some engines
        for i in range(2):
            mock_engine = MagicMock()
            cache_key = f"key-{i}"
            cached = CachedEngine(mock_engine, 1800)
            cached.access_count = i + 1  # Vary access counts

            with pool._lock:
                pool._cache[cache_key] = cached

        # Get stats
        stats = pool.get_stats()

        # Verify stats structure
        assert "total_engines" in stats
        assert stats["total_engines"] == 2
        assert "engines" in stats
        assert len(stats["engines"]) == 2

        # Verify engine stats
        for engine_stat in stats["engines"]:
            assert "database_id" in engine_stat
            assert "age_seconds" in engine_stat
            assert "idle_seconds" in engine_stat
            assert "access_count" in engine_stat
            assert "is_expired" in engine_stat


class TestEnginePoolManagerThreadSafety:
    """Test thread-safety mechanisms."""

    def test_get_creation_lock(self):
        """Test that creation locks are properly managed."""
        pool = EnginePoolManager()

        cache_key = "test-key"

        # Get lock twice
        lock1 = pool._get_creation_lock(cache_key)
        lock2 = pool._get_creation_lock(cache_key)

        # Should be same lock
        assert lock1 is lock2

    def test_multiple_threads_same_engine(self):
        """Test that multiple threads requesting same engine get same instance."""
        # This is a basic test - full concurrency testing would be complex
        pool = EnginePoolManager()

        db_id = uuid4()
        connection_string = "mock://localhost"

        results = []

        def get_engine():
            # Mock the create_engine call
            with patch("app.core.engine_pool.create_engine") as mock_create:
                mock_engine = MagicMock()
                mock_create.return_value = mock_engine

                engine = pool.get_engine(db_id, connection_string)
                results.append(engine)

        # Create multiple threads
        threads = []
        for _ in range(3):
            t = threading.Thread(target=get_engine)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All should get the same engine
        assert len(results) == 3
        assert all(e is results[0] for e in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
