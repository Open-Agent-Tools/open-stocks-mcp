"""Regression tests for rate-limiter isolation across unit tests."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any
from unittest.mock import patch

import pytest

from open_stocks_mcp.tools.options.positions import (
    get_aggregate_positions,
    get_all_option_positions,
    get_open_option_positions,
)
from open_stocks_mcp.tools.rate_limiter import get_rate_limiter

_bucket_filled_in_previous_test = False


@pytest.mark.journey_system
@pytest.mark.unit
def test_rate_limiter_reset_clears_state() -> None:
    """Reset clears all global limiter state."""
    limiter = get_rate_limiter()
    now = time.time()

    for _ in range(limiter.calls_per_minute):
        limiter.call_times.append(now)
    limiter.endpoint_buckets["options"].append(now)

    assert limiter.get_stats()["calls_last_minute"] == limiter.calls_per_minute
    assert limiter.endpoint_buckets

    limiter.reset()
    stats = limiter.get_stats()

    assert stats["calls_last_minute"] == 0
    assert stats["calls_last_hour"] == 0
    assert limiter.endpoint_buckets == {}


@pytest.mark.journey_system
@pytest.mark.unit
def test_autouse_fixture_seed_rate_limiter_for_next_test() -> None:
    """Seed the limiter so the next test can prove fixture isolation."""
    global _bucket_filled_in_previous_test

    limiter = get_rate_limiter()
    now = time.time()
    for _ in range(limiter.calls_per_minute):
        limiter.call_times.append(now)

    _bucket_filled_in_previous_test = True
    assert limiter.get_stats()["calls_last_minute"] == limiter.calls_per_minute


@pytest.mark.journey_system
@pytest.mark.unit
def test_autouse_fixture_prevents_cross_test_bleed() -> None:
    """Autouse reset fixture should clear global limiter state between tests."""
    assert _bucket_filled_in_previous_test is True

    limiter = get_rate_limiter()
    stats = limiter.get_stats()

    assert stats["calls_last_minute"] == 0
    assert stats["calls_last_hour"] == 0
    assert len(limiter.call_times) == 0
    assert limiter.endpoint_buckets == {}


@pytest.mark.journey_system
@pytest.mark.unit
@pytest.mark.asyncio
async def test_option_position_tools_complete_fast() -> None:
    """Previously flaky option-position calls should return quickly."""
    cases: list[
        tuple[str, Callable[[], Awaitable[dict[str, Any]]], Any]
    ] = [
        (
            "open_stocks_mcp.tools.options.positions.rh.options.get_aggregate_positions",
            get_aggregate_positions,
            [],
        ),
        (
            "open_stocks_mcp.tools.options.positions.rh.options.get_all_option_positions",
            get_all_option_positions,
            [
                {
                    "chain_symbol": "AAPL",
                    "type": "long",
                    "quantity": "1.0000",
                    "average_buy_price": "5.25",
                }
            ],
        ),
        (
            "open_stocks_mcp.tools.options.positions.rh.options.get_open_option_positions",
            get_open_option_positions,
            [
                {
                    "chain_symbol": "AAPL",
                    "type": "long",
                    "quantity": "1.0000",
                }
            ],
        ),
        (
            "open_stocks_mcp.tools.options.positions.rh.options.get_open_option_positions",
            get_open_option_positions,
            None,
        ),
    ]

    for target, tool_fn, payload in cases:
        with patch(target, return_value=payload):
            started = perf_counter()
            result = await asyncio.wait_for(tool_fn(), timeout=2.0)
            elapsed = perf_counter() - started
            assert "result" in result
            assert elapsed < 2.0
