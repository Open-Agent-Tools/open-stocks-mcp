"""Simple tests for rate limiter without time delays."""

import asyncio
from typing import Any
from unittest.mock import patch

import pytest

from open_stocks_mcp.tools.rate_limiter import (
    RateLimiter,
    get_broker_rate_limit_defaults,
    get_rate_limiter,
    rate_limited_call,
)


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

    @pytest.mark.unit
    def test_rate_limiter_constants_defined_and_used(self) -> None:
        """Verify that rate limiter constants are exported and used as defaults."""
        from open_stocks_mcp.tools.rate_limiter import (
            BURST_WINDOW_SECONDS,
            DEFAULT_BURST_SIZE,
            DEFAULT_CALLS_PER_HOUR,
            DEFAULT_CALLS_PER_MINUTE,
            SECONDS_PER_HOUR,
            SECONDS_PER_MINUTE,
            reset_global_rate_limiter,
        )

        # Check values
        assert SECONDS_PER_MINUTE == 60
        assert SECONDS_PER_HOUR == 3600
        assert BURST_WINDOW_SECONDS == 1
        assert DEFAULT_CALLS_PER_MINUTE == 30
        assert DEFAULT_CALLS_PER_HOUR == 1000
        assert DEFAULT_BURST_SIZE == 5

        # Reset and check get_rate_limiter defaults
        reset_global_rate_limiter()
        limiter = get_rate_limiter()
        assert limiter.calls_per_minute == DEFAULT_CALLS_PER_MINUTE
        assert limiter.calls_per_hour == DEFAULT_CALLS_PER_HOUR
        assert limiter.burst_size == DEFAULT_BURST_SIZE

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
    async def test_hourly_limit_waits_until_oldest_hour_entry_expires(
        self, mock_sleep: Any, mock_time: Any
    ) -> None:
        """Hourly limit waits are based on the oldest call in the hour window."""
        current_time: dict[str, float] = {"value": 3000.0}

        async def fake_sleep(duration: float) -> None:
            current_time["value"] += duration + 0.001

        mock_time.side_effect = lambda: current_time["value"]
        mock_sleep.side_effect = fake_sleep

        limiter = RateLimiter(calls_per_minute=10, calls_per_hour=2, burst_size=10)
        limiter.call_times.extend([1000.0, 2000.0])

        await asyncio.wait_for(limiter.acquire(), timeout=1)

        mock_sleep.assert_awaited_once()
        assert mock_sleep.await_args.args[0] == pytest.approx(1600.0)
        assert list(limiter.call_times) == pytest.approx([2000.0, 4600.001])

    @patch("open_stocks_mcp.tools.rate_limiter.time.time")
    @patch("open_stocks_mcp.tools.rate_limiter.asyncio.sleep")
    @pytest.mark.journey_system
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_burst_limit_sleeps_without_real_delay(
        self, mock_sleep: Any, mock_time: Any
    ) -> None:
        """Burst overflow waits for the oldest burst-window call to expire."""
        current_time: dict[str, float] = {"value": 1000.0}

        async def fake_sleep(duration: float) -> None:
            current_time["value"] += duration + 0.001

        mock_time.side_effect = lambda: current_time["value"]
        mock_sleep.side_effect = fake_sleep

        limiter = RateLimiter(calls_per_minute=10, calls_per_hour=100, burst_size=2)
        limiter.call_times.extend([999.3, 999.6])

        await asyncio.wait_for(limiter.acquire(), timeout=1)

        mock_sleep.assert_awaited_once()
        sleep_duration = mock_sleep.await_args.args[0]
        assert 0 < sleep_duration < 1
        assert sleep_duration == pytest.approx(0.3)
        assert len(limiter.call_times) == 3

    @patch("open_stocks_mcp.tools.rate_limiter.time.time")
    @patch("open_stocks_mcp.tools.rate_limiter.asyncio.sleep")
    @pytest.mark.journey_system
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_acquire_prunes_minute_and_hour_windows(
        self, mock_sleep: Any, mock_time: Any
    ) -> None:
        """Expired hourly entries are pruned and minute stats reset after 60s."""
        mock_time.return_value = 5000.0
        mock_sleep.return_value = None

        limiter = RateLimiter(calls_per_minute=2, calls_per_hour=5, burst_size=5)
        limiter.call_times.extend([1000.0, 4939.0])

        await limiter.acquire()

        mock_sleep.assert_not_awaited()
        assert 1000.0 not in limiter.call_times
        assert list(limiter.call_times) == [4939.0, 5000.0]

        stats = limiter.get_stats()
        assert stats["calls_last_minute"] == 1
        assert stats["calls_last_hour"] == 2

    @patch("open_stocks_mcp.tools.rate_limiter.time.time")
    @patch("open_stocks_mcp.tools.rate_limiter.asyncio.sleep")
    @pytest.mark.journey_system
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_acquire_serializes_under_lock_contention(
        self, mock_sleep: Any, mock_time: Any
    ) -> None:
        """Concurrent acquires complete and record one call per successful task."""
        current_time: dict[str, float] = {"value": 1000.0}

        def fake_time() -> float:
            current_time["value"] += 0.001
            return current_time["value"]

        mock_time.side_effect = fake_time
        mock_sleep.return_value = None

        limiter = RateLimiter(calls_per_minute=100, calls_per_hour=100, burst_size=100)
        acquire_count = 8

        await asyncio.wait_for(
            asyncio.gather(*(limiter.acquire() for _ in range(acquire_count))),
            timeout=1,
        )

        mock_sleep.assert_not_awaited()
        assert len(limiter.call_times) == acquire_count
        assert list(limiter.call_times) == sorted(limiter.call_times)

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


def test_get_broker_rate_limit_defaults() -> None:
    robinhood = get_broker_rate_limit_defaults("robinhood")
    schwab = get_broker_rate_limit_defaults("schwab")

    assert robinhood == (30, 1000, 5)
    assert schwab[0] >= 120


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


@pytest.mark.journey_system
@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limited_call_runs_sync_function_without_deprecated_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_acquire(_endpoint: str | None = None) -> None:
        return None

    monkeypatch.setattr(get_rate_limiter(), "acquire", fake_acquire)
    monkeypatch.setattr(
        "open_stocks_mcp.tools.rate_limiter.asyncio.get_event_loop",
        lambda: (_ for _ in ()).throw(AssertionError("deprecated loop lookup")),
    )

    def add(a: int, b: int) -> int:
        return a + b

    result = await rate_limited_call(add, 2, 3)
    assert result == 5


@pytest.mark.journey_system
@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limited_call_routes_to_broker_limiter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    acquire_calls: list[str | None] = []

    class StubLimiter:
        async def acquire(self, endpoint: str | None = None) -> None:
            acquire_calls.append(endpoint)

    def fake_get_rate_limiter(broker_name: str | None = None) -> StubLimiter:
        assert broker_name == "schwab"
        return StubLimiter()

    monkeypatch.setattr(
        "open_stocks_mcp.tools.rate_limiter.get_rate_limiter", fake_get_rate_limiter
    )

    async def ok() -> str:
        return "ok"

    result = await rate_limited_call(ok, endpoint="/quote", broker_name="schwab")
    assert result == "ok"
    assert acquire_calls == ["/quote"]
