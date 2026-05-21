"""CI-safe performance smoke tests for representative MCP tool calls.

All broker/API dependencies are mocked so these tests run without credentials
or live network access. Timing assertions use conservative thresholds (0.5s per
call) to catch pathological regressions without depending on machine speed.

Run with:
    uv run pytest tests/performance -k smoke -q
"""

import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

_MOCK_QUOTE_DATA = [
    {
        "last_trade_price": "150.22",
        "bid_price": "150.20",
        "ask_price": "150.25",
        "previous_close": "148.50",
        "volume": "50000000",
    }
]
_MOCK_PRICE_DATA = ["150.25"]
_MOCK_ACCOUNT_DATA = {"username": "test_user", "created_at": "2024-01-01T00:00:00Z"}


def _make_schwab_quote_response(symbol: str) -> dict[str, Any]:
    return {
        symbol.upper(): {
            "quote": {
                "lastPrice": 150.22,
                "bidPrice": 150.20,
                "askPrice": 150.25,
                "totalVolume": 50000000,
            }
        }
    }


@pytest.mark.asyncio
async def test_get_stock_price_smoke_performance() -> None:
    """get_stock_price completes under 0.5 s with mocked broker dependencies."""
    call_results = iter([_MOCK_PRICE_DATA, _MOCK_QUOTE_DATA])

    async def mock_execute_with_retry(fn: Any, *args: Any, **kwargs: Any) -> Any:
        return next(call_results)

    with patch(
        "open_stocks_mcp.tools.robinhood_stock_tools.execute_with_retry",
        side_effect=mock_execute_with_retry,
    ):
        from open_stocks_mcp.tools.robinhood_stock_tools import get_stock_price

        start = time.perf_counter()
        result = await get_stock_price("AAPL")
        elapsed = time.perf_counter() - start

    assert "result" in result
    assert result["result"]["symbol"] == "AAPL"
    assert elapsed < 0.5, f"get_stock_price took {elapsed:.3f}s (limit 0.5s)"


@pytest.mark.asyncio
async def test_get_account_info_smoke_performance() -> None:
    """get_account_info completes under 0.5 s with mocked broker dependencies."""

    async def mock_execute_with_retry(fn: Any, *args: Any, **kwargs: Any) -> Any:
        return _MOCK_ACCOUNT_DATA

    with patch(
        "open_stocks_mcp.tools.robinhood_account_tools.execute_with_retry",
        side_effect=mock_execute_with_retry,
    ):
        from open_stocks_mcp.tools.robinhood_account_tools import get_account_info

        start = time.perf_counter()
        result = await get_account_info()
        elapsed = time.perf_counter() - start

    assert "result" in result
    assert result["result"]["username"] == "test_user"
    assert elapsed < 0.5, f"get_account_info took {elapsed:.3f}s (limit 0.5s)"


@pytest.mark.asyncio
async def test_get_schwab_quote_smoke_performance() -> None:
    """get_schwab_quote completes under 0.5 s with mocked broker/client."""
    mock_response = MagicMock()
    mock_response.json.return_value = _make_schwab_quote_response("AAPL")

    mock_broker = MagicMock()
    mock_broker.client.get_quote.return_value = mock_response

    async def mock_get_broker(*args: Any, **kwargs: Any) -> tuple[Any, None]:
        return mock_broker, None

    with patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error",
        side_effect=mock_get_broker,
    ):
        from open_stocks_mcp.tools.schwab_market_tools import get_schwab_quote

        start = time.perf_counter()
        result = await get_schwab_quote("AAPL")
        elapsed = time.perf_counter() - start

    assert "result" in result
    assert result["result"]["symbol"] == "AAPL"
    assert elapsed < 0.5, f"get_schwab_quote took {elapsed:.3f}s (limit 0.5s)"
