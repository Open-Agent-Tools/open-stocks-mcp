"""Simple tests for rate limiter without time delays."""

import asyncio
from typing import Any
from unittest.mock import patch

import pytest

from open_stocks_mcp.tools.rate_limiter import RateLimiter, get_rate_limiter


class TestSimpleRateLimiter:
    """Test RateLimiter with mocked time to avoid delays."""

    @pytest.mark.journey_system
    @pytest.mark.unit
    def test_rate_limiter_creation(self) -> None:
        """Test that rate limiter can be created."""
        limiter = RateLimiter(calls_per_minute=60)
        assert limiter.calls_per_minute == 60
        assert limiter.calls_per_hour == 1800  # default
        assert limiter.burst_size == 10  # default

    @pytest.mark.journey_system
    @pytest.mark.unit
    def test_rate_limiter_custom_settings(self) -> None:
        """Test rate limiter with custom settings."""
        limiter = RateLimiter(calls_per_minute=30, calls_per_hour=900, burst_size=5)
        assert limiter.calls_per_minute == 30
        assert limiter.calls_per_hour == 900
        assert limiter.burst_size == 5

    @pytest.mark.journey_system
    @pytest.mark.unit
    def test_get_stats(self) -> None:
        """Test that get_stats returns proper structure."""
        limiter = RateLimiter(calls_per_minute=60)
        stats = limiter.get_stats()

        assert isinstance(stats, dict)
        assert "calls_last_minute" in stats
        assert "calls_last_hour" in stats
        assert "limit_per_minute" in stats
        assert "limit_per_hour" in stats
        assert "burst_size" in stats
        assert "minute_usage_percent" in stats
        assert "hour_usage_percent" in stats
        assert "endpoint_usage" in stats

    @pytest.mark.journey_system
    @pytest.mark.unit
    def test_get_rate_limiter_singleton(self) -> None:
        """Test that get_rate_limiter returns a RateLimiter instance."""
        limiter = get_rate_limiter()
        assert isinstance(limiter, RateLimiter)

        # Should return same instance (singleton pattern)
        limiter2 = get_rate_limiter()
        assert limiter is limiter2

    @patch("open_stocks_mcp.tools.rate_limiter.time.time")
    @patch("open_stocks_mcp.tools.rate_limiter.asyncio.sleep")
    @pytest.mark.journey_system
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_acquire_basic(self, mock_sleep: Any, mock_time: Any) -> None:
        """Test basic acquire functionality."""
        mock_time.return_value = 1000.0
        mock_sleep.return_value = None

        limiter = RateLimiter(calls_per_minute=60)

        # Should not sleep on first call
        await limiter.acquire()
        mock_sleep.assert_not_called()

        # Should have recorded the call
        assert len(limiter.call_times) == 1

    @patch("open_stocks_mcp.tools.rate_limiter.time.time")
    @patch("open_stocks_mcp.tools.rate_limiter.asyncio.sleep")
    @pytest.mark.journey_system
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_stats_includes_endpoint_and_broker_usage(
        self, mock_sleep: Any, mock_time: Any
    ) -> None:
        """Endpoint and broker usage stats should be additive to legacy keys."""
        mock_time.return_value = 1000.0
        mock_sleep.return_value = None

        limiter = RateLimiter(calls_per_minute=60)
        await limiter.acquire(endpoint="/quotes", broker="robinhood")
        await limiter.acquire(endpoint="/quotes", broker="robinhood")
        await limiter.acquire(endpoint="/orders", broker="schwab")

        stats = limiter.get_stats()

        assert stats["calls_last_minute"] == 3
        assert stats["endpoint_usage"]["/quotes"]["calls_last_minute"] == 2
        assert stats["endpoint_usage"]["/orders"]["calls_last_minute"] == 1
        assert stats["broker_usage"]["robinhood"]["calls_last_minute"] == 2
        assert stats["broker_usage"]["schwab"]["calls_last_minute"] == 1


@pytest.mark.journey_system
@pytest.mark.unit
def test_configure_global_rate_limiter_updates_singleton() -> None:
    from open_stocks_mcp.tools.rate_limiter import (
        configure_global_rate_limiter,
        reset_global_rate_limiter,
    )

    reset_global_rate_limiter()
    limiter = configure_global_rate_limiter(11, 222, 3)

    assert limiter.calls_per_minute == 11
    assert limiter.calls_per_hour == 222
    assert limiter.burst_size == 3
    assert get_rate_limiter() is limiter


class TestRequestCoordinator:
    """Test RequestCoordinator singleflight deduplication logic."""

    @pytest.mark.journey_system
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_coalesce_concurrent_same_key(self) -> None:
        """Concurrent calls with the same key share one underlying coroutine."""
        from open_stocks_mcp.tools.rate_limiter import RequestCoordinator

        coordinator = RequestCoordinator()
        call_count = 0

        async def slow_fetch() -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0)
            return "result"

        results = await asyncio.gather(
            coordinator.execute("key-A", slow_fetch),
            coordinator.execute("key-A", slow_fetch),
        )

        assert call_count == 1
        assert list(results) == ["result", "result"]

    @pytest.mark.journey_system
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_coalesce_independent_keys(self) -> None:
        """Different keys execute independently (no deduplication)."""
        from open_stocks_mcp.tools.rate_limiter import RequestCoordinator

        coordinator = RequestCoordinator()
        call_count = 0

        async def fetch() -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0)
            return "result"

        results = await asyncio.gather(
            coordinator.execute("key-A", fetch),
            coordinator.execute("key-B", fetch),
        )

        assert call_count == 2
        assert list(results) == ["result", "result"]

    @pytest.mark.journey_system
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_coalesce_failed_call_cleanup(self) -> None:
        """Failed calls are cleaned up from the in-flight map so next call executes fresh."""
        from open_stocks_mcp.tools.rate_limiter import RequestCoordinator

        coordinator = RequestCoordinator()

        async def failing_fetch() -> str:
            raise ValueError("broker error")

        with pytest.raises(ValueError, match="broker error"):
            await coordinator.execute("key-A", failing_fetch)

        assert "key-A" not in coordinator._in_flight

        call_count = 0

        async def ok_fetch() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await coordinator.execute("key-A", ok_fetch)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.journey_system
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initial_caller_cancellation_releases_waiters(self) -> None:
        """Cancellation of the first caller does not leave coalesced waiters pending."""
        from open_stocks_mcp.tools.rate_limiter import RequestCoordinator

        coordinator = RequestCoordinator()
        started = asyncio.Event()

        async def slow_fetch() -> str:
            started.set()
            await asyncio.sleep(60)
            return "result"

        first = asyncio.create_task(coordinator.execute("key-A", slow_fetch))
        await started.wait()
        second = asyncio.create_task(coordinator.execute("key-A", slow_fetch))
        await asyncio.sleep(0)

        first.cancel()

        with pytest.raises(asyncio.CancelledError):
            await first
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(second, timeout=1)

        assert "key-A" not in coordinator._in_flight

    @pytest.mark.journey_system
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_coalesced_count_increments(self) -> None:
        """coalesced_count tracks how many calls were deduplicated."""
        from open_stocks_mcp.tools.rate_limiter import RequestCoordinator

        coordinator = RequestCoordinator()

        async def slow_fetch() -> str:
            await asyncio.sleep(0)
            return "result"

        await asyncio.gather(
            coordinator.execute("key-A", slow_fetch),
            coordinator.execute("key-A", slow_fetch),
            coordinator.execute("key-A", slow_fetch),
        )

        assert coordinator.coalesced_count == 2

    @pytest.mark.journey_system
    @pytest.mark.unit
    def test_get_request_coordinator_singleton(self) -> None:
        """get_request_coordinator returns the same instance each time."""
        from open_stocks_mcp.tools.rate_limiter import get_request_coordinator

        c1 = get_request_coordinator()
        c2 = get_request_coordinator()
        assert c1 is c2
