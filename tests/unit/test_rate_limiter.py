"""Unit tests for queued rate limiting and request batching."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from open_stocks_mcp.config import load_config
from open_stocks_mcp.tools.rate_limiter import RateLimiter


@pytest.mark.unit
class TestRateLimiterQueueing:
    """Test RateLimiter queue and drain behavior."""

    @patch("open_stocks_mcp.tools.rate_limiter.time.time")
    @patch("open_stocks_mcp.tools.rate_limiter.asyncio.sleep")
    @pytest.mark.asyncio
    async def test_acquire_queues_when_limit_reached(self, mock_sleep, mock_time):
        """Second caller should queue when limit is 1 per minute."""
        # Setup: 1 call per minute, 10 per hour, burst 1
        limiter = RateLimiter(calls_per_minute=1, calls_per_hour=10, burst_size=1)

        # First call at T=1000
        mock_time.return_value = 1000.0
        await limiter.acquire()
        assert len(limiter.call_times) == 1
        mock_sleep.assert_not_called()

        # Second call immediately after
        # It should sleep until T=1060 (1000 + 60)
        mock_time.return_value = 1000.1

        # We need to simulate time passing during sleep
        async def side_effect(delay):
            mock_time.return_value += delay

        mock_sleep.side_effect = side_effect

        await limiter.acquire()

        # Should have slept for roughly 60s (1000 + 60 - 1000.1 = 59.9)
        # Note: the exact sleep call depends on implementation.
        # If it's the current recursive implementation, it sleeps 59.9.
        assert mock_sleep.called
        assert len(limiter.call_times) == 2
        assert limiter.call_times[-1] >= 1060.0

    @patch("open_stocks_mcp.tools.rate_limiter.time.time")
    @patch("open_stocks_mcp.tools.rate_limiter.asyncio.sleep")
    @pytest.mark.asyncio
    async def test_acquire_max_wait_exceeded(self, mock_sleep, mock_time):
        """Should raise error if max_wait is exceeded."""
        limiter = RateLimiter(calls_per_minute=1, calls_per_hour=10, burst_size=1)

        # First call fills the minute
        mock_time.return_value = 1000.0
        await limiter.acquire()

        # Second call with max_wait=1.0 (but needs 60s)
        mock_time.return_value = 1000.1

        from open_stocks_mcp.tools.exceptions import RateLimitError

        with pytest.raises(
            RateLimitError, match=r"Rate limit wait time .* exceeds max_wait"
        ):
            await limiter.acquire(max_wait=1.0)


@pytest.mark.unit
class TestBatchConfig:
    """Test parsing of batching configuration."""

    def test_load_config_with_batch_env(self, monkeypatch):
        """Verify batch config is loaded from environment variables."""
        monkeypatch.setenv("OPEN_STOCKS_MCP_BATCH_SIZE", "5")
        monkeypatch.setenv("OPEN_STOCKS_MCP_QUEUE_MAX_WAIT", "0.25")

        config = load_config()
        assert config.batch.batch_size == 5
        assert config.batch.queue_max_wait == 0.25


@pytest.mark.unit
class TestBatchingHelper:
    """Test reusable batching helper."""

    @pytest.mark.asyncio
    async def test_batching_helper_coalesces_requests(self):
        """Concurrent requests within window should be coalesced."""
        from open_stocks_mcp.tools.rate_limiter import get_batcher

        # Use a fresh batcher for testing
        batcher = get_batcher("test-batcher", batch_size=3, queue_max_wait=0.1)

        fetch_many = MagicMock()
        fetch_many.side_effect = lambda symbols: {s: f"data-{s}" for s in symbols}

        results = await asyncio.gather(
            batcher.fetch("AAPL", fetch_many),
            batcher.fetch("MSFT", fetch_many),
            batcher.fetch("GOOGL", fetch_many),
        )

        assert results == ["data-AAPL", "data-MSFT", "data-GOOGL"]
        assert fetch_many.call_count == 1
        # Symbols should be uppercased and passed as a list
        called_symbols = fetch_many.call_args[0][0]
        assert set(called_symbols) == {"AAPL", "MSFT", "GOOGL"}
