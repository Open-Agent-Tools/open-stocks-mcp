"""Unit tests for Schwab trading tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.schwab_trading_tools import (
    cancel_schwab_order,
    get_schwab_order_by_id,
    get_schwab_orders,
    place_schwab_order,
    schwab_buy_limit,
    schwab_buy_market,
    schwab_sell_limit,
    schwab_sell_market,
)


class TestSchwabTradingTools:
    """Test Schwab trading tools with mocked responses."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.equity_buy_market")
    async def test_buy_market_success(
        self,
        mock_equity_buy_market: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful market buy order."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock order spec
        mock_equity_buy_market.return_value = {"orderType": "MARKET"}

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/orders/12345"}
        mock_to_thread.return_value = mock_response

        result = await schwab_buy_market("abc123", "AAPL", 10)

        assert "result" in result
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["action"] == "buy"
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["quantity"] == 10
        assert result["result"]["order_id"] == "12345"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error")
    async def test_buy_market_auth_error(self, mock_get_broker: AsyncMock) -> None:
        """Test market buy when authentication fails."""
        # Mock authentication error
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        result = await schwab_buy_market("abc123", "AAPL", 10)

        assert result == error_response

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.equity_sell_market")
    async def test_sell_market_success(
        self,
        mock_equity_sell_market: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful market sell order."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock order spec
        mock_equity_sell_market.return_value = {"orderType": "MARKET"}

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Location": "/orders/67890"}
        mock_to_thread.return_value = mock_response

        result = await schwab_sell_market("abc123", "AAPL", 5)

        assert "result" in result
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["action"] == "sell"
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["order_id"] == "67890"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.equity_buy_limit")
    async def test_buy_limit_success(
        self,
        mock_equity_buy_limit: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful limit buy order."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock order spec
        mock_equity_buy_limit.return_value = {"orderType": "LIMIT"}

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/orders/11111"}
        mock_to_thread.return_value = mock_response

        result = await schwab_buy_limit("abc123", "AAPL", 10, 175.00)

        assert "result" in result
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["order_type"] == "limit"
        assert result["result"]["limit_price"] == 175.00

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.equity_sell_limit")
    async def test_sell_limit_success(
        self,
        mock_equity_sell_limit: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful limit sell order."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock order spec
        mock_equity_sell_limit.return_value = {"orderType": "LIMIT"}

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Location": "/orders/22222"}
        mock_to_thread.return_value = mock_response

        result = await schwab_sell_limit("abc123", "AAPL", 5, 180.00)

        assert "result" in result
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["order_type"] == "limit"
        assert result["result"]["limit_price"] == 180.00

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    async def test_get_orders_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful orders retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock response
        mock_to_thread.return_value = [
            {
                "orderId": 12345,
                "orderType": "MARKET",
                "status": "FILLED",
                "orderLegCollection": [
                    {"instrument": {"symbol": "AAPL"}, "quantity": 10}
                ],
            },
            {
                "orderId": 67890,
                "orderType": "LIMIT",
                "status": "WORKING",
                "orderLegCollection": [
                    {"instrument": {"symbol": "GOOGL"}, "quantity": 5}
                ],
            },
        ]

        result = await get_schwab_orders("abc123", max_results=50)

        assert "result" in result
        assert "orders" in result["result"]
        assert result["result"]["count"] == 2

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    async def test_cancel_order_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful order cancellation."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_to_thread.return_value = mock_response

        result = await cancel_schwab_order("abc123", "12345")

        assert "result" in result
        assert result["result"]["status"] == "order_cancelled"
        assert result["result"]["order_id"] == "12345"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    async def test_get_order_by_id_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful order retrieval by ID."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock response
        mock_to_thread.return_value = {
            "orderId": 12345,
            "orderType": "MARKET",
            "status": "FILLED",
            "filledQuantity": 10.0,
            "orderLegCollection": [
                {"instrument": {"symbol": "AAPL"}, "quantity": 10}
            ],
        }

        result = await get_schwab_order_by_id("abc123", "12345")

        assert "result" in result
        assert result["result"]["orderId"] == 12345
        assert result["result"]["status"] == "FILLED"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    async def test_place_order_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful generic order placement."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/orders/99999"}
        mock_to_thread.return_value = mock_response

        order_spec = {"orderType": "MARKET", "orderLegCollection": []}
        result = await place_schwab_order("abc123", order_spec)

        assert "result" in result
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["order_id"] == "99999"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.equity_buy_market")
    async def test_buy_market_error(
        self,
        mock_equity_buy_market: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test market buy order error handling."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock order spec
        mock_equity_buy_market.return_value = {"orderType": "MARKET"}

        # Mock API error
        mock_to_thread.side_effect = Exception("API Error")

        result = await schwab_buy_market("abc123", "AAPL", 10)

        assert "result" in result
        assert "error" in result["result"]
