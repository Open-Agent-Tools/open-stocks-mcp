"""Unit tests for Schwab trading tools."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.schwab_trading_tools import (
    cancel_schwab_order,
    get_schwab_order_by_id,
    get_schwab_orders,
    get_schwab_transaction,
    place_schwab_order,
    schwab_buy_limit,
    schwab_buy_market,
    schwab_get_transactions,
    schwab_get_transactions_by_date,
    schwab_sell_limit,
    schwab_sell_market,
)


def _assert_retry_safe(mock_execute_broker_request: AsyncMock, expected: bool) -> None:
    call_args = mock_execute_broker_request.call_args
    assert call_args is not None
    _, kwargs = call_args
    assert kwargs.get("retry_safe") is expected


class TestSchwabTradingTools:
    """Test Schwab trading tools with mocked responses."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
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
        _assert_retry_safe(mock_to_thread, False)

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
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
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
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
        _assert_retry_safe(mock_to_thread, False)

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
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
        _assert_retry_safe(mock_to_thread, False)

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
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
        _assert_retry_safe(mock_to_thread, False)

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
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
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
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
        _assert_retry_safe(mock_to_thread, False)

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
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
            "orderLegCollection": [{"instrument": {"symbol": "AAPL"}, "quantity": 10}],
        }

        result = await get_schwab_order_by_id("abc123", "12345")

        assert "result" in result
        assert result["result"]["orderId"] == 12345
        assert result["result"]["status"] == "FILLED"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    async def test_get_transactions_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful transactions retrieval."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.return_value = [
            {"transactionId": 1, "symbol": "AAPL"},
            {"transactionId": 2, "symbol": "MSFT"},
        ]

        result = await schwab_get_transactions("abc123")

        assert result["result"]["transactions"] == [
            {"transactionId": 1, "symbol": "AAPL"},
            {"transactionId": 2, "symbol": "MSFT"},
        ]
        assert result["result"]["count"] == 2

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    async def test_get_transactions_empty(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test empty transactions list."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.return_value = []

        result = await schwab_get_transactions("abc123")

        assert result["result"]["transactions"] == []
        assert result["result"]["count"] == 0

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    async def test_get_transactions_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Test auth error passthrough for transactions."""
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        result = await schwab_get_transactions("abc123")
        assert result == error_response

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    async def test_get_transactions_with_filters(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test filters are passed through to Schwab client."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.return_value = [{"transactionId": 1, "symbol": "AAPL"}]

        await schwab_get_transactions(
            "abc123",
            start_date="2026-04-01",
            end_date="2026-04-30",
            transaction_types=["TRADE"],
            symbol="AAPL",
        )

        call_args = mock_to_thread.call_args
        assert call_args is not None
        args, kwargs = call_args
        assert args[0] is mock_broker.client.get_transactions
        assert args[1] == "abc123"
        assert kwargs["start_date"] == datetime.date(2026, 4, 1)
        assert kwargs["end_date"] == datetime.date(2026, 4, 30)
        assert kwargs["transaction_types"] == ["TRADE"]
        assert kwargs["symbol"] == "AAPL"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    async def test_get_transactions_by_date_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test date-scoped transactions retrieval."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.return_value = [{"transactionId": 1}, {"transactionId": 2}]

        result = await schwab_get_transactions_by_date(
            "abc123", "2026-04-01", "2026-04-30"
        )

        assert result["result"]["transactions"] == [
            {"transactionId": 1},
            {"transactionId": 2},
        ]
        assert result["result"]["count"] == 2
        call_args = mock_to_thread.call_args
        assert call_args is not None
        args, kwargs = call_args
        assert args[0] is mock_broker.client.get_transactions
        assert args[1] == "abc123"
        assert kwargs["start_date"] == datetime.date(2026, 4, 1)
        assert kwargs["end_date"] == datetime.date(2026, 4, 30)

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
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
        _assert_retry_safe(mock_to_thread, False)

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_trading_tools.equity_buy_market")
    async def test_buy_market_api_failure(
        self,
        mock_equity_buy_market: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test market buy order API failure (non-201 status)."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock order spec
        mock_equity_buy_market.return_value = {"orderType": "MARKET"}

        # Mock response with error status
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid order"
        mock_to_thread.return_value = mock_response

        result = await schwab_buy_market("abc123", "AAPL", 10)

        assert "result" in result
        assert result["result"]["status"] == "error"
        assert "Invalid order" in result["result"]["error"]
        _assert_retry_safe(mock_to_thread, False)

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_cancel_order_api_failure(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test order cancellation API failure."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock response with error status
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Order not found"
        mock_to_thread.return_value = mock_response

        result = await cancel_schwab_order("abc123", "12345")

        assert "result" in result
        assert result["result"]["status"] == "error"
        assert "Order not found" in result["result"]["error"]
        _assert_retry_safe(mock_to_thread, False)

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.exception_test
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
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
        _assert_retry_safe(mock_to_thread, False)

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    @pytest.mark.parametrize(
        "function,args",
        [
            (schwab_sell_market, ("abc123", "AAPL", 5)),
            (schwab_buy_limit, ("abc123", "AAPL", 10, 175.00)),
            (schwab_sell_limit, ("abc123", "AAPL", 5, 180.00)),
            (get_schwab_order_by_id, ("abc123", "12345")),
            (place_schwab_order, ("abc123", {"orderType": "MARKET"})),
        ],
    )
    async def test_trading_api_failures_bulk(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        function,
        args,
    ) -> None:
        """Test various trading tools for API failure responses."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Using side_effect covers both status-checking and non-status-checking functions
        mock_to_thread.side_effect = Exception("Internal Server Error")

        result = await function(*args)
        assert result["result"]["status"] == "error"
        assert "Internal Server Error" in result["result"]["error"]
        if function in {
            schwab_sell_market,
            schwab_buy_limit,
            schwab_sell_limit,
            place_schwab_order,
        }:
            _assert_retry_safe(mock_to_thread, False)

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    async def test_get_transaction_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful transaction retrieval by ID."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_to_thread.return_value = {
            "transactionId": "abc",
            "type": "TRADE",
            "netAmount": 100.0,
        }

        result = await get_schwab_transaction("abc123", "abc")

        assert "result" in result
        assert result["result"]["transactionId"] == "abc"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    async def test_get_transaction_auth_error(self, mock_get_broker: AsyncMock) -> None:
        """Test transaction retrieval when authentication fails."""
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        result = await get_schwab_transaction("abc123", "abc")

        assert result == error_response

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.exception_test
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.asyncio.to_thread")
    async def test_get_transaction_api_error(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test transaction retrieval error handling."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_to_thread.side_effect = Exception("API Error")

        result = await get_schwab_transaction("abc123", "abc")

        assert "result" in result
        assert "error" in result["result"]


class TestSchwabPlaceOrderMCPWrapper:
    """Test schwab_place_order MCP wrapper in server app."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.server.app._place_schwab_order_impl")
    async def test_schwab_place_order_mcp_wrapper(
        self, mock_impl: AsyncMock
    ) -> None:
        """Test schwab_place_order wrapper delegates to impl with exact args."""
        from open_stocks_mcp.server.app import schwab_place_order

        expected = {"result": {"status": "order_placed", "order_id": "1"}}
        mock_impl.return_value = expected

        order_spec: dict = {"orderType": "MARKET", "quantity": 1}
        result = await schwab_place_order("hash123", order_spec)

        mock_impl.assert_awaited_once_with("hash123", order_spec)
        assert result == expected
