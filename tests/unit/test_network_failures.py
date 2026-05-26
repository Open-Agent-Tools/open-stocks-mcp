"""Tool-level network failure scenario tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_stocks_mcp.tools.schwab_market_tools import get_schwab_quote
from open_stocks_mcp.tools.stocks.quote import get_stock_price

pytestmark = [
    pytest.mark.unit,
    pytest.mark.journey_system,
    pytest.mark.exception_test,
]


@pytest.mark.asyncio
async def test_robinhood_stock_price_timeout_returns_structured_error() -> None:
    with patch(
        "open_stocks_mcp.tools.stocks.quote.execute_with_retry",
        new=AsyncMock(side_effect=TimeoutError("request timeout")),
    ):
        result = await get_stock_price("AAPL")

    assert result["result"]["status"] == "error"
    assert result["result"]["error_type"] == "network"
    assert result["result"]["error"]


@pytest.mark.asyncio
async def test_schwab_quote_connection_refused_returns_structured_error() -> None:
    fake_client = SimpleNamespace(
        get_quote=lambda _symbol: SimpleNamespace(json=lambda: {"AAPL": {"quote": {}}})
    )
    fake_broker = SimpleNamespace(client=fake_client)
    with (
        patch(
            "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error",
            new=AsyncMock(return_value=(fake_broker, None)),
        ),
        patch(
            "open_stocks_mcp.tools.schwab_market_tools.execute_broker_request",
            new=AsyncMock(side_effect=ConnectionError("connection refused")),
        ),
    ):
        result = await get_schwab_quote("AAPL")

    assert result["result"]["status"] == "error"
    assert result["result"]["error_type"] == "network"
    assert result["result"]["error"]
