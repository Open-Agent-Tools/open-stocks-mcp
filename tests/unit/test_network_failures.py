"""Exception-scenario tests for network failures in representative tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.robinhood_stock_tools import get_stock_price
from open_stocks_mcp.tools.schwab_market_tools import get_schwab_quote

pytestmark = [pytest.mark.unit, pytest.mark.journey_system, pytest.mark.exception_test]


@pytest.mark.asyncio
async def test_robinhood_stock_price_timeout_returns_structured_error() -> None:
    with patch(
        "open_stocks_mcp.tools.robinhood_stock_tools.execute_with_retry",
        new=AsyncMock(side_effect=TimeoutError("request timeout")),
    ):
        result = await get_stock_price("AAPL")

    assert result["result"]["status"] == "error"
    assert result["result"]["error_type"] == "network"
    assert result["result"]["error"] == "Network connectivity issue"


@pytest.mark.asyncio
async def test_schwab_quote_connection_refused_returns_structured_error() -> None:
    fake_broker = MagicMock()
    fake_broker.client = MagicMock()

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
    assert result["result"]["error"] == "Network connectivity issue"
