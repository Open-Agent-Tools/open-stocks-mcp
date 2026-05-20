"""Unit tests for RobinhoodBroker delegation paths (no live API calls)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.brokers.base import BrokerAuthStatus
from open_stocks_mcp.brokers.robinhood import RobinhoodBroker


@pytest.fixture()
def broker() -> RobinhoodBroker:
    session_mgr = MagicMock()
    session_mgr.is_session_valid.return_value = True
    rb = RobinhoodBroker(session_manager=session_mgr)
    rb._auth_info.status = BrokerAuthStatus.AUTHENTICATED
    return rb


@pytest.fixture()
def unavailable_broker() -> RobinhoodBroker:
    session_mgr = MagicMock()
    session_mgr.is_session_valid.return_value = False
    rb = RobinhoodBroker(session_manager=session_mgr)
    rb._auth_info.status = BrokerAuthStatus.NOT_CONFIGURED
    return rb


class TestGetStockQuoteDelegation:
    """get_stock_quote must delegate to get_stock_price tool, not return a stub."""

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delegates_to_stock_price_tool(self, broker: RobinhoodBroker) -> None:
        expected = {"result": {"symbol": "AAPL", "price": 150.0}}
        with patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.get_stock_price",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.get_stock_quote("AAPL")

        mock_tool.assert_awaited_once_with("AAPL")
        assert result == expected

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_unavailable_when_not_authenticated(
        self, unavailable_broker: RobinhoodBroker
    ) -> None:
        result = await unavailable_broker.get_stock_quote("AAPL")
        assert result["result"]["status"] == "broker_unavailable"

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_is_not_not_implemented(self, broker: RobinhoodBroker) -> None:
        with patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.get_stock_price",
            new=AsyncMock(return_value={"result": {"price": 1.0}}),
        ):
            result = await broker.get_stock_quote("TSLA")

        assert result.get("result", {}).get("status") != "not_implemented"

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_delegated_error_response(
        self, broker: RobinhoodBroker
    ) -> None:
        """Delegated error responses are returned unchanged."""
        expected = {
            "result": {
                "status": "error",
                "error": "Invalid symbol format: 123INVALID",
            }
        }

        with patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.get_stock_price",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.get_stock_quote("123INVALID")

        assert result == expected
        mock_tool.assert_awaited_once_with("123INVALID")


class TestOtherRobinhoodDelegations:
    """The other Robinhood methods must also delegate cleanly without stubs."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_account_info_delegates(self, broker: RobinhoodBroker) -> None:
        expected = {"result": {"accounts": []}}
        with patch(
            "open_stocks_mcp.tools.robinhood_account_tools.get_account_info",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.get_account_info()

        mock_tool.assert_awaited_once()
        assert result == expected

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_portfolio_delegates(self, broker: RobinhoodBroker) -> None:
        expected = {"result": {"portfolio": {}}}
        with patch(
            "open_stocks_mcp.tools.robinhood_account_tools.get_portfolio",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.get_portfolio()

        mock_tool.assert_awaited_once()
        assert result == expected

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_positions_delegates(self, broker: RobinhoodBroker) -> None:
        expected = {"result": {"positions": []}}
        with patch(
            "open_stocks_mcp.tools.robinhood_account_tools.get_positions",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.get_positions()

        mock_tool.assert_awaited_once()
        assert result == expected

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_stock_price_delegates(self, broker: RobinhoodBroker) -> None:
        expected = {"result": {"price": 99.0}}
        with patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.get_stock_price",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.get_stock_price("GOOGL")

        mock_tool.assert_awaited_once_with("GOOGL")
        assert result == expected
