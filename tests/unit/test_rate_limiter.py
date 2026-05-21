"""Focused tests for queued rate limiting and symbol batching."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from open_stocks_mcp.config import load_config
from open_stocks_mcp.tools.rate_limiter import RateLimiter, batch_fetch_symbols


class TestQueuedRateLimiter:
    """Queue/drain behavior for the rate limiter."""

    @pytest.mark.journey_system
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.rate_limiter.asyncio.sleep", new_callable=AsyncMock)
    @patch("open_stocks_mcp.tools.rate_limiter.time.time")
    async def test_queue_drains_fifo(self, mock_time: Any, _mock_sleep: Any) -> None:
        limiter = RateLimiter(calls_per_minute=1, calls_per_hour=10, burst_size=1)
        time_values = iter([100.0, 100.0, 100.0, 100.0, 160.1, 160.1])
        mock_time.side_effect = lambda: next(time_values)

        await limiter.acquire(max_wait=0.5)
        await limiter.acquire(max_wait=0.5)

        assert len(limiter.call_times) == 2

    @pytest.mark.journey_system
    @pytest.mark.unit
    def test_batch_config_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPEN_STOCKS_MCP_BATCH_SIZE", "3")
        monkeypatch.setenv("OPEN_STOCKS_MCP_QUEUE_MAX_WAIT", "0.25")

        config = load_config()

        assert config.batch.batch_size == 3
        assert config.batch.queue_max_wait == 0.25


class TestBatchHelper:
    """Symbol batching helper behavior."""

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_batch_helper_coalesces_symbol_burst(self) -> None:
        calls: list[list[str]] = []

        async def fetch_many(symbols: list[str]) -> list[dict[str, Any]]:
            calls.append(symbols)
            return [{"symbol": s, "id": f"id-{s}"} for s in symbols]

        async def request_one(symbol: str) -> list[dict[str, Any] | None]:
            return await batch_fetch_symbols(
                "test-symbol-burst",
                [symbol],
                fetch_many,
                batch_size=3,
                queue_max_wait=0.01,
            )

        results = await asyncio.gather(
            request_one("AAPL"), request_one("MSFT"), request_one("GOOGL")
        )

        assert len(calls) == 1
        assert calls[0] == ["AAPL", "MSFT", "GOOGL"]
        assert results[0][0] == {"symbol": "AAPL", "id": "id-AAPL"}
        assert results[1][0] == {"symbol": "MSFT", "id": "id-MSFT"}
        assert results[2][0] == {"symbol": "GOOGL", "id": "id-GOOGL"}
