"""Unit tests for the in-memory caching layer."""

from __future__ import annotations

import asyncio
import importlib
import time
from collections.abc import Iterator
from typing import Any
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _reset_cache_state() -> Iterator[None]:
    """Reset shared cache + metrics state between tests."""
    from open_stocks_mcp import monitoring
    from open_stocks_mcp.tools import cache

    cache.clear_caches()
    monitoring._metrics_collector = None
    yield
    cache.clear_caches()
    monitoring._metrics_collector = None


class TestCachedAsyncDecorator:
    """Tests for the cached_async decorator."""

    @pytest.mark.unit
    @pytest.mark.journey_system
    @pytest.mark.asyncio
    async def test_cache_hit_returns_memoized_value(self) -> None:
        from open_stocks_mcp.tools.cache import cached_async

        call_count = 0

        @cached_async(name="hit", ttl=60)
        async def fetch(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        first = await fetch(3)
        second = await fetch(3)

        assert first == 6
        assert second == 6
        assert call_count == 1

    @pytest.mark.unit
    @pytest.mark.journey_system
    @pytest.mark.asyncio
    async def test_cache_miss_invokes_wrapped_callable(self) -> None:
        from open_stocks_mcp.tools.cache import cached_async

        call_count = 0

        @cached_async(name="miss", ttl=60)
        async def fetch(symbol: str) -> str:
            nonlocal call_count
            call_count += 1
            return symbol.upper()

        await fetch("aapl")
        await fetch("msft")

        assert call_count == 2

    @pytest.mark.unit
    @pytest.mark.journey_system
    @pytest.mark.asyncio
    async def test_ttl_expiry_forces_reinvocation(self) -> None:
        from open_stocks_mcp.tools.cache import cached_async

        call_count = 0
        clock = {"value": 1000.0}

        def fake_monotonic() -> float:
            return clock["value"]

        @cached_async(name="ttl", ttl=5, clock=fake_monotonic)
        async def fetch() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        first = await fetch()
        # Advance clock past the TTL
        clock["value"] += 6
        second = await fetch()

        assert first == 1
        assert second == 2
        assert call_count == 2

    @pytest.mark.unit
    @pytest.mark.journey_system
    @pytest.mark.asyncio
    async def test_lru_eviction_discards_least_recently_used(self) -> None:
        from open_stocks_mcp.tools.cache import cached_async

        call_count = 0

        @cached_async(name="lru", max_size=2, strategy="lru")
        async def fetch(key: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"{key}-{call_count}"

        a1 = await fetch("a")
        b1 = await fetch("b")
        # Touch "a" to make "b" the LRU
        await fetch("a")
        # Insert "c" — should evict "b"
        await fetch("c")

        # Re-fetching "a" should still hit cache (no new call)
        before = call_count
        await fetch("a")
        assert call_count == before, "fetch('a') should be a cache hit"

        # Re-fetching "b" should miss and re-invoke
        b2 = await fetch("b")
        assert b2 != b1
        assert a1 == "a-1"

    @pytest.mark.unit
    @pytest.mark.journey_system
    @pytest.mark.asyncio
    async def test_distinct_args_produce_distinct_entries(self) -> None:
        from open_stocks_mcp.tools.cache import cached_async

        call_count = 0

        @cached_async(name="keys", ttl=60)
        async def fetch(*args: Any, **kwargs: Any) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        await fetch(1)
        await fetch(2)
        await fetch(1, mode="x")
        await fetch(1, mode="x")  # repeat, cache hit
        await fetch(1, mode="y")

        assert call_count == 4

    @pytest.mark.unit
    @pytest.mark.journey_system
    @pytest.mark.asyncio
    async def test_concurrent_calls_run_underlying_once(self) -> None:
        from open_stocks_mcp.tools.cache import cached_async

        call_count = 0

        @cached_async(name="concurrent", ttl=60)
        async def fetch() -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return call_count

        results = await asyncio.gather(*(fetch() for _ in range(8)))

        assert call_count == 1
        assert all(r == 1 for r in results)

    @pytest.mark.unit
    @pytest.mark.journey_system
    @pytest.mark.asyncio
    async def test_records_hit_and_miss_into_metrics(self) -> None:
        from open_stocks_mcp.monitoring import get_metrics_collector
        from open_stocks_mcp.tools.cache import cached_async

        @cached_async(name="metrics-target", ttl=60)
        async def fetch(x: int) -> int:
            return x

        await fetch(1)  # miss
        await fetch(1)  # hit
        await fetch(2)  # miss
        await fetch(1)  # hit

        metrics = await get_metrics_collector().get_metrics()

        cache_hits = metrics["cache_hits"]
        cache_misses = metrics["cache_misses"]
        assert cache_hits["metrics-target"] == 2
        assert cache_misses["metrics-target"] == 2
        assert metrics["cache_hit_rate_percent"]["metrics-target"] == 50.0


class TestCacheConfig:
    """Tests for CacheConfig loading from environment."""

    @pytest.mark.unit
    @pytest.mark.journey_system
    def test_defaults_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from open_stocks_mcp.config import load_config

        for var in (
            "CACHE_QUOTES_TTL",
            "CACHE_ACCOUNT_TTL",
            "CACHE_MAX_SIZE",
            "CACHE_STRATEGY",
        ):
            monkeypatch.delenv(var, raising=False)

        cfg = load_config()

        assert cfg.cache.quotes_ttl_seconds == 15
        assert cfg.cache.account_ttl_seconds == 300
        assert cfg.cache.max_size == 1024
        assert cfg.cache.strategy == "ttl"

    @pytest.mark.unit
    @pytest.mark.journey_system
    def test_env_overrides_apply(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from open_stocks_mcp.config import load_config

        monkeypatch.setenv("CACHE_QUOTES_TTL", "7")
        monkeypatch.setenv("CACHE_ACCOUNT_TTL", "120")
        monkeypatch.setenv("CACHE_MAX_SIZE", "16")
        monkeypatch.setenv("CACHE_STRATEGY", "lru")

        cfg = load_config()

        assert cfg.cache.quotes_ttl_seconds == 7
        assert cfg.cache.account_ttl_seconds == 120
        assert cfg.cache.max_size == 16
        assert cfg.cache.strategy == "lru"


class TestToolIntegration:
    """Tests that cache decorator is applied to the target tools."""

    @pytest.mark.unit
    @pytest.mark.journey_market_data
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_quotes",
        return_value=[
            {
                "previous_close": "100.00",
                "volume": "1000",
                "ask_price": "101.00",
                "bid_price": "100.50",
                "last_trade_price": "100.75",
            }
        ],
    )
    @patch(
        "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_latest_price",
        return_value=["101.00"],
    )
    async def test_get_stock_price_uses_cache(
        self, mock_price: Any, mock_quote: Any
    ) -> None:
        from open_stocks_mcp.tools.robinhood_stock_tools import get_stock_price

        first = await get_stock_price("AAPL")
        second = await get_stock_price("AAPL")

        assert first["result"]["price"] == 101.0
        assert second["result"]["price"] == 101.0
        # Cached: underlying API called exactly once across two invocations
        assert mock_price.call_count == 1
        assert mock_quote.call_count == 1

        # Distinct symbol bypasses cache
        await get_stock_price("MSFT")
        assert mock_price.call_count == 2

    @pytest.mark.unit
    @pytest.mark.journey_market_data
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_quotes",
        return_value=[
            {
                "previous_close": "100.00",
                "volume": "1000",
                "ask_price": "101.00",
                "bid_price": "100.50",
                "last_trade_price": "100.75",
            }
        ],
    )
    @patch(
        "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_latest_price",
        return_value=["101.00"],
    )
    async def test_get_stock_price_refetches_after_ttl(
        self, mock_price: Any, mock_quote: Any
    ) -> None:
        from open_stocks_mcp.tools import cache, robinhood_stock_tools

        # Replace the real clock for the wrapped cache entry
        clock = {"value": time.monotonic()}
        cache.clear_caches()

        original = robinhood_stock_tools.get_stock_price
        # Walk past every existing decorator down to the raw coroutine, so the
        # fresh test wrapper isn't shadowed by the production cache.
        raw = original
        while hasattr(raw, "__wrapped__"):
            raw = raw.__wrapped__
        rewrapped = cache.cached_async(
            name="quotes", ttl=5, clock=lambda: clock["value"]
        )(raw)

        try:
            robinhood_stock_tools.get_stock_price = rewrapped  # type: ignore[assignment]
            await robinhood_stock_tools.get_stock_price("AAPL")
            await robinhood_stock_tools.get_stock_price("AAPL")
            assert mock_price.call_count == 1

            clock["value"] += 10
            await robinhood_stock_tools.get_stock_price("AAPL")
            assert mock_price.call_count == 2
        finally:
            robinhood_stock_tools.get_stock_price = original  # type: ignore[assignment]

    @pytest.mark.unit
    @pytest.mark.journey_portfolio
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.robinhood_account_tools.rh.load_portfolio_profile",
        return_value={
            "market_value": "1000.00",
            "equity": "1200.00",
            "buying_power": "500.00",
        },
    )
    async def test_get_portfolio_uses_cache(self, mock_portfolio: Any) -> None:
        from open_stocks_mcp.tools.robinhood_account_tools import get_portfolio

        first = await get_portfolio()
        second = await get_portfolio()

        assert first["result"]["market_value"] == "1000.00"
        assert second["result"]["market_value"] == "1000.00"
        assert mock_portfolio.call_count == 1

    @pytest.mark.unit
    @pytest.mark.journey_system
    @pytest.mark.asyncio
    async def test_tool_decorators_use_configured_lru_strategy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from open_stocks_mcp.tools import (
            cache,
            robinhood_account_tools,
            robinhood_stock_tools,
        )

        try:
            with monkeypatch.context() as env:
                env.setenv("CACHE_STRATEGY", "lru")
                env.setenv("CACHE_QUOTES_TTL", "0")
                env.setenv("CACHE_ACCOUNT_TTL", "0")
                cache.clear_caches()

                stock_tools = importlib.reload(robinhood_stock_tools)
                account_tools = importlib.reload(robinhood_account_tools)

                with (
                    patch.object(
                        stock_tools.rh,
                        "get_quotes",
                        return_value=[
                            {
                                "previous_close": "100.00",
                                "volume": "1000",
                                "ask_price": "101.00",
                                "bid_price": "100.50",
                                "last_trade_price": "100.75",
                            }
                        ],
                    ) as mock_quote,
                    patch.object(
                        stock_tools.rh,
                        "get_latest_price",
                        return_value=["101.00"],
                    ) as mock_price,
                    patch.object(
                        account_tools.rh,
                        "load_portfolio_profile",
                        return_value={
                            "market_value": "1000.00",
                            "equity": "1200.00",
                            "buying_power": "500.00",
                        },
                    ) as mock_portfolio,
                ):
                    await stock_tools.get_stock_price("AAPL")
                    await stock_tools.get_stock_price("AAPL")
                    await account_tools.get_portfolio()
                    await account_tools.get_portfolio()

                assert mock_price.call_count == 1
                assert mock_quote.call_count == 1
                assert mock_portfolio.call_count == 1
        finally:
            cache.clear_caches()
            importlib.reload(robinhood_stock_tools)
            importlib.reload(robinhood_account_tools)

    @pytest.mark.unit
    @pytest.mark.journey_system
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.robinhood_account_tools.rh.load_portfolio_profile",
        return_value={
            "market_value": "1000.00",
            "equity": "1200.00",
            "buying_power": "500.00",
        },
    )
    @patch(
        "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_quotes",
        return_value=[
            {
                "previous_close": "100.00",
                "volume": "1000",
                "ask_price": "101.00",
                "bid_price": "100.50",
                "last_trade_price": "100.75",
            }
        ],
    )
    @patch(
        "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_latest_price",
        return_value=["101.00"],
    )
    async def test_metrics_record_per_tool_cache_names(
        self, mock_price: Any, mock_quote: Any, mock_portfolio: Any
    ) -> None:
        from open_stocks_mcp.monitoring import get_metrics_collector
        from open_stocks_mcp.tools.robinhood_account_tools import get_portfolio
        from open_stocks_mcp.tools.robinhood_stock_tools import get_stock_price

        await get_stock_price("AAPL")
        await get_stock_price("AAPL")
        await get_portfolio()
        await get_portfolio()

        metrics = await get_metrics_collector().get_metrics()
        assert metrics["cache_misses"].get("quotes", 0) == 1
        assert metrics["cache_hits"].get("quotes", 0) == 1
        assert metrics["cache_misses"].get("account", 0) == 1
        assert metrics["cache_hits"].get("account", 0) == 1
