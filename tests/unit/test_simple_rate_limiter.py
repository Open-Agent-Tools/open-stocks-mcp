"""Simple tests for rate limiter without time delays."""

from typing import Any
from unittest.mock import patch

import pytest

from open_stocks_mcp.tools.rate_limiter import RateLimiter, get_rate_limiter


class TestSimpleRateLimiter:
    """Test RateLimiter with mocked time to avoid delays."""

    def test_rate_limiter_creation(self) -> None:
        """Test that rate limiter can be created."""
        limiter = RateLimiter(calls_per_minute=60)
        assert limiter.calls_per_minute == 60
        assert limiter.calls_per_hour == 1800  # default
        assert limiter.burst_size == 10  # default

    def test_rate_limiter_custom_settings(self) -> None:
        """Test rate limiter with custom settings."""
        limiter = RateLimiter(calls_per_minute=30, calls_per_hour=900, burst_size=5)
        assert limiter.calls_per_minute == 30
        assert limiter.calls_per_hour == 900
        assert limiter.burst_size == 5

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

    def test_get_rate_limiter_singleton(self) -> None:
        """Test that get_rate_limiter returns a RateLimiter instance."""
        limiter = get_rate_limiter()
        assert isinstance(limiter, RateLimiter)

        # Should return same instance (singleton pattern)
        limiter2 = get_rate_limiter()
        assert limiter is limiter2

    @patch("open_stocks_mcp.tools.rate_limiter.time.time")
    @patch("open_stocks_mcp.tools.rate_limiter.asyncio.sleep")
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
