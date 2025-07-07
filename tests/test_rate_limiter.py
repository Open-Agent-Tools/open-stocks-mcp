"""Tests for rate_limiter module."""

import asyncio
import time

import pytest

from open_stocks_mcp.tools.rate_limiter import (
    RateLimiter,
    get_rate_limiter,
    rate_limited_call,
)


class TestRateLimiter:
    """Test RateLimiter class."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter with fast limits for testing."""
        return RateLimiter(calls_per_minute=5, calls_per_hour=100, burst_size=3)

    @pytest.mark.asyncio
    async def test_basic_rate_limiting(self, rate_limiter):
        """Test basic rate limiting functionality."""
        # Should allow burst_size calls immediately
        start = time.time()
        for _ in range(rate_limiter.burst_size):
            await rate_limiter.acquire()

        # Time should be minimal for burst
        assert time.time() - start < 0.1

        # Next call should be delayed
        start = time.time()
        await rate_limiter.acquire()
        elapsed = time.time() - start

        # Should have waited approximately 1 second
        assert 0.9 < elapsed < 1.2

    @pytest.mark.asyncio
    async def test_minute_limit(self, rate_limiter):
        """Test per-minute rate limiting."""
        # Make calls up to the minute limit
        for _ in range(rate_limiter.calls_per_minute):
            await rate_limiter.acquire()

        # Next call should be delayed
        start = time.time()
        await rate_limiter.acquire()
        elapsed = time.time() - start

        # Should have waited some time
        assert elapsed > 0.5

    @pytest.mark.asyncio
    async def test_get_stats(self, rate_limiter):
        """Test getting rate limiter statistics."""
        # Make some calls
        for _ in range(3):
            await rate_limiter.acquire()

        stats = rate_limiter.get_stats()

        assert stats["calls_last_minute"] == 3
        assert stats["calls_last_hour"] == 3
        assert stats["limit_per_minute"] == 5
        assert stats["limit_per_hour"] == 100
        assert stats["burst_size"] == 3
        assert 50 < stats["minute_usage_percent"] < 70
        assert stats["hour_usage_percent"] == 3.0

    @pytest.mark.asyncio
    async def test_endpoint_tracking(self, rate_limiter):
        """Test per-endpoint tracking."""
        await rate_limiter.acquire("endpoint1")
        await rate_limiter.acquire("endpoint2")
        await rate_limiter.acquire("endpoint1")

        # Check endpoint buckets
        assert len(rate_limiter.endpoint_buckets["endpoint1"]) == 2
        assert len(rate_limiter.endpoint_buckets["endpoint2"]) == 1

    @pytest.mark.asyncio
    async def test_weight_parameter(self, rate_limiter):
        """Test weighted calls."""
        # Make a call with weight 3
        await rate_limiter.acquire(weight=3)

        stats = rate_limiter.get_stats()
        assert stats["calls_last_minute"] == 3

    @pytest.mark.asyncio
    async def test_concurrent_calls(self, rate_limiter):
        """Test concurrent rate limiting."""

        # Create multiple concurrent calls
        async def make_call(i):
            await rate_limiter.acquire()
            return i

        # Should handle concurrent calls properly
        results = await asyncio.gather(*[make_call(i) for i in range(5)])

        assert len(results) == 5
        assert set(results) == {0, 1, 2, 3, 4}


class TestRateLimiterGlobal:
    """Test global rate limiter functionality."""

    def test_get_rate_limiter_singleton(self):
        """Test that get_rate_limiter returns singleton."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        assert limiter1 is limiter2

    @pytest.mark.asyncio
    async def test_rate_limited_call_async(self):
        """Test rate_limited_call with async function."""
        call_count = 0

        async def async_func():
            nonlocal call_count
            call_count += 1
            return "async_result"

        result = await rate_limited_call(async_func)

        assert result == "async_result"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limited_call_sync(self):
        """Test rate_limited_call with sync function."""
        call_count = 0

        def sync_func():
            nonlocal call_count
            call_count += 1
            return "sync_result"

        result = await rate_limited_call(sync_func)

        assert result == "sync_result"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limited_call_with_endpoint(self):
        """Test rate_limited_call with endpoint tracking."""

        async def test_func():
            return "test"

        # Make calls with different endpoints
        await rate_limited_call(test_func, endpoint="api1")
        await rate_limited_call(test_func, endpoint="api2")
        await rate_limited_call(test_func, endpoint="api1")

        limiter = get_rate_limiter()
        assert len(limiter.endpoint_buckets["api1"]) >= 2
        assert len(limiter.endpoint_buckets["api2"]) >= 1


class TestRateLimiterIntegration:
    """Integration tests for rate limiter."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_rate_limiter_prevents_bursts(self):
        """Test that rate limiter prevents rapid bursts."""
        limiter = RateLimiter(calls_per_minute=10, calls_per_hour=100, burst_size=2)

        times = []

        # Make 5 calls and record times
        for _ in range(5):
            start = time.time()
            await limiter.acquire()
            times.append(time.time() - start)

        # First 2 should be immediate (burst)
        assert times[0] < 0.1
        assert times[1] < 0.1

        # Rest should be delayed
        assert times[2] > 0.5
        assert times[3] > 0.5
        assert times[4] > 0.5
