"""Unit tests for Robinhood broker stock quote delegation."""

from unittest.mock import AsyncMock, patch

import pytest

from open_stocks_mcp.brokers.base import BrokerAuthStatus
from open_stocks_mcp.brokers.robinhood import RobinhoodBroker


@pytest.fixture
def robinhood_broker() -> RobinhoodBroker:
    """Create a Robinhood broker instance for testing."""
    return RobinhoodBroker()


@pytest.mark.journey_market_data
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_stock_quote_delegates_to_get_stock_price_success(
    robinhood_broker: RobinhoodBroker,
) -> None:
    """Delegates quote lookups to the live stock price tool path."""
    robinhood_broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
    expected = {
        "result": {
            "symbol": "AAPL",
            "price": 150.25,
            "previous_close": 148.5,
            "volume": 1000000,
            "ask_price": 150.30,
            "bid_price": 150.20,
            "last_trade_price": 150.25,
            "status": "success",
        }
    }

    with patch(
        "open_stocks_mcp.tools.robinhood_stock_tools.get_stock_price",
        new=AsyncMock(return_value=expected),
    ) as mock_get_stock_price:
        result = await robinhood_broker.get_stock_quote("AAPL")

    assert result == expected
    mock_get_stock_price.assert_awaited_once_with("AAPL")


@pytest.mark.journey_market_data
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_stock_quote_unavailable_broker_does_not_call_tool(
    robinhood_broker: RobinhoodBroker,
) -> None:
    """Unavailable broker returns standardized response without tool delegation."""
    robinhood_broker._auth_info.status = BrokerAuthStatus.NOT_CONFIGURED

    with patch(
        "open_stocks_mcp.tools.robinhood_stock_tools.get_stock_price",
        new=AsyncMock(),
    ) as mock_get_stock_price:
        result = await robinhood_broker.get_stock_quote("AAPL")

    assert result["result"]["status"] == "broker_unavailable"
    assert result["result"]["broker"] == "robinhood"
    mock_get_stock_price.assert_not_called()


@pytest.mark.journey_market_data
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_stock_quote_returns_delegated_error_response(
    robinhood_broker: RobinhoodBroker,
) -> None:
    """Delegated error responses are returned unchanged."""
    robinhood_broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
    expected = {
        "result": {
            "status": "error",
            "error": "Invalid symbol format: 123INVALID",
        }
    }

    with patch(
        "open_stocks_mcp.tools.robinhood_stock_tools.get_stock_price",
        new=AsyncMock(return_value=expected),
    ) as mock_get_stock_price:
        result = await robinhood_broker.get_stock_quote("123INVALID")

    assert result == expected
    mock_get_stock_price.assert_awaited_once_with("123INVALID")
