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
        function: Any,
        args: tuple[Any, ...],
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

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_schwab_place_order_wrapper_delegates_to_tool(self) -> None:
        """The server-layer schwab_place_order tool delegates to place_schwab_order."""
        from unittest.mock import AsyncMock, patch

        from open_stocks_mcp.server import app as server_app

        account_hash = "abc123"
        order_spec = {"orderType": "MARKET", "orderLegCollection": []}
        expected_payload = {
            "result": {
                "status": "order_placed",
                "order_id": "99999",
                "status_code": 201,
            }
        }

        with patch.object(
            server_app, "place_schwab_order", new=AsyncMock(return_value=expected_payload)
        ) as mock_place:
            result = await server_app.schwab_place_order(account_hash, order_spec)

            mock_place.assert_awaited_once_with(account_hash, order_spec)
            assert result is expected_payload


# ============================================================
# New tools from Issue #196
# ============================================================


class TestSchwabOrderSellStop:
    """Tests for schwab_order_sell_stop."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_sell_stop_success(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful stop-sell order placement."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/orders/99001"}
        mock_execute.return_value = mock_response

        from open_stocks_mcp.tools.schwab_trading_tools import schwab_order_sell_stop

        result = await schwab_order_sell_stop("acct1", "AAPL", 5, "148.00")

        assert result["result"]["status"] == "order_placed"
        assert result["result"]["action"] == "sell"
        assert result["result"]["order_type"] == "stop"
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["quantity"] == 5
        assert result["result"]["order_id"] == "99001"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    async def test_sell_stop_auth_error(self, mock_get_broker: AsyncMock) -> None:
        """Test stop-sell order when authentication fails."""
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        from open_stocks_mcp.tools.schwab_trading_tools import schwab_order_sell_stop

        result = await schwab_order_sell_stop("acct1", "AAPL", 5, "148.00")
        assert result == error_response

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_sell_stop_api_error_response(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test stop-sell detects API error status codes."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid stop price"
        mock_execute.return_value = mock_response

        from open_stocks_mcp.tools.schwab_trading_tools import schwab_order_sell_stop

        result = await schwab_order_sell_stop("acct1", "AAPL", 5, "148.00")
        assert "error" in result["result"]


class TestSchwabGetOpenStockOrders:
    """Tests for schwab_get_open_stock_orders."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_get_open_stock_orders_filters_correctly(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test that only open equity orders are returned."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        orders = [
            # Open equity order — should be included
            {
                "orderId": "1",
                "status": "WORKING",
                "orderLegCollection": [
                    {"instrument": {"assetType": "EQUITY", "symbol": "AAPL"}}
                ],
            },
            # Filled equity order — excluded
            {
                "orderId": "2",
                "status": "FILLED",
                "orderLegCollection": [
                    {"instrument": {"assetType": "EQUITY", "symbol": "MSFT"}}
                ],
            },
            # Open option order — excluded (not equity)
            {
                "orderId": "3",
                "status": "WORKING",
                "orderLegCollection": [
                    {
                        "instrument": {
                            "assetType": "OPTION",
                            "symbol": "AAPL  251219C00150000",
                        }
                    }
                ],
            },
        ]
        mock_execute.return_value = orders

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_get_open_stock_orders,
        )

        result = await schwab_get_open_stock_orders("acct1")
        assert result["result"]["count"] == 1
        assert result["result"]["orders"][0]["orderId"] == "1"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    async def test_get_open_stock_orders_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Test get_open_stock_orders auth failure."""
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_get_open_stock_orders,
        )

        result = await schwab_get_open_stock_orders("acct1")
        assert result == error_response


class TestSchwabCancelAllStockOrders:
    """Tests for schwab_cancel_all_stock_orders."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_cancel_all_stock_orders_success(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test cancelling all open stock orders successfully."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        open_orders_response = [
            {
                "orderId": "10",
                "status": "WORKING",
                "orderLegCollection": [
                    {"instrument": {"assetType": "EQUITY", "symbol": "AAPL"}}
                ],
            },
            {
                "orderId": "11",
                "status": "NEW",
                "orderLegCollection": [
                    {"instrument": {"assetType": "EQUITY", "symbol": "TSLA"}}
                ],
            },
        ]

        cancel_response = MagicMock()
        cancel_response.status_code = 200

        mock_execute.side_effect = [
            open_orders_response,  # get open orders
            cancel_response,  # cancel order 10
            cancel_response,  # cancel order 11
        ]

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_cancel_all_stock_orders,
        )

        result = await schwab_cancel_all_stock_orders("acct1")
        assert result["result"]["cancelled_count"] == 2
        assert result["result"]["failed_count"] == 0

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_cancel_all_stock_orders_partial_failure(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test cancel_all_stock_orders when some cancellations fail."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        open_orders_response = [
            {
                "orderId": "20",
                "status": "WORKING",
                "orderLegCollection": [
                    {"instrument": {"assetType": "EQUITY", "symbol": "AAPL"}}
                ],
            },
            {
                "orderId": "21",
                "status": "WORKING",
                "orderLegCollection": [
                    {"instrument": {"assetType": "EQUITY", "symbol": "TSLA"}}
                ],
            },
        ]

        ok_response = MagicMock()
        ok_response.status_code = 200

        fail_response = MagicMock()
        fail_response.status_code = 422
        fail_response.text = "Already cancelled"

        mock_execute.side_effect = [
            open_orders_response,
            ok_response,
            fail_response,
        ]

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_cancel_all_stock_orders,
        )

        result = await schwab_cancel_all_stock_orders("acct1")
        assert result["result"]["cancelled_count"] == 1
        assert result["result"]["failed_count"] == 1

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    async def test_cancel_all_stock_orders_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Test cancel_all_stock_orders auth failure."""
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_cancel_all_stock_orders,
        )

        result = await schwab_cancel_all_stock_orders("acct1")
        assert result == error_response


class TestSchwabOrderBuyOptionLimit:
    """Tests for schwab_order_buy_option_limit."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_buy_option_limit_success(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful option limit buy order."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/orders/30001"}
        mock_execute.return_value = mock_response

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_buy_option_limit,
        )

        result = await schwab_order_buy_option_limit(
            "acct1", "AAPL  251219C00150000", 2, "5.50"
        )
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["action"] == "buy_to_open"
        assert result["result"]["order_type"] == "limit"
        assert result["result"]["quantity"] == 2
        assert result["result"]["order_id"] == "30001"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_buy_option_limit_api_failure(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test option buy limit detects API error."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid option symbol"
        mock_execute.return_value = mock_response

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_buy_option_limit,
        )

        result = await schwab_order_buy_option_limit("acct1", "BAD_SYMBOL", 1, "3.00")
        assert "error" in result["result"]

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    async def test_buy_option_limit_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Test buy_option_limit auth failure."""
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_buy_option_limit,
        )

        result = await schwab_order_buy_option_limit(
            "acct1", "AAPL  251219C00150000", 1, "5.00"
        )
        assert result == error_response


class TestSchwabOrderSellOptionLimit:
    """Tests for schwab_order_sell_option_limit."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_sell_option_limit_success(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful option limit sell order."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/orders/40001"}
        mock_execute.return_value = mock_response

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_sell_option_limit,
        )

        result = await schwab_order_sell_option_limit(
            "acct1", "AAPL  251219C00150000", 2, "4.00"
        )
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["action"] == "sell_to_close"
        assert result["result"]["order_type"] == "limit"
        assert result["result"]["order_id"] == "40001"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    async def test_sell_option_limit_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Test sell_option_limit auth failure."""
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_sell_option_limit,
        )

        result = await schwab_order_sell_option_limit(
            "acct1", "AAPL  251219C00150000", 1, "4.00"
        )
        assert result == error_response


class TestSchwabCancelOptionOrder:
    """Tests for schwab_cancel_option_order."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_cancel_option_order_success(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test cancelling a specific option order."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_execute.return_value = mock_response

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_cancel_option_order,
        )

        result = await schwab_cancel_option_order("acct1", "opt_order_55")
        assert result["result"]["status"] == "order_cancelled"
        assert result["result"]["order_id"] == "opt_order_55"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    async def test_cancel_option_order_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Test cancel_option_order auth failure."""
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_cancel_option_order,
        )

        result = await schwab_cancel_option_order("acct1", "opt_order_55")
        assert result == error_response


class TestSchwabCancelAllOptionOrders:
    """Tests for schwab_cancel_all_option_orders."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_cancel_all_option_orders_ignores_equity(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test cancel_all_option_orders ignores equity orders."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        all_orders = [
            # Open option order — should be cancelled
            {
                "orderId": "opt1",
                "status": "WORKING",
                "orderLegCollection": [
                    {
                        "instrument": {
                            "assetType": "OPTION",
                            "symbol": "AAPL  251219C00150000",
                        }
                    }
                ],
            },
            # Open equity order — should be skipped
            {
                "orderId": "eq1",
                "status": "WORKING",
                "orderLegCollection": [
                    {"instrument": {"assetType": "EQUITY", "symbol": "AAPL"}}
                ],
            },
            # Filled option — excluded
            {
                "orderId": "opt2",
                "status": "FILLED",
                "orderLegCollection": [
                    {
                        "instrument": {
                            "assetType": "OPTION",
                            "symbol": "AAPL  251219P00140000",
                        }
                    }
                ],
            },
        ]

        cancel_response = MagicMock()
        cancel_response.status_code = 200

        mock_execute.side_effect = [
            all_orders,
            cancel_response,
        ]

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_cancel_all_option_orders,
        )

        result = await schwab_cancel_all_option_orders("acct1")
        assert result["result"]["cancelled_count"] == 1
        assert result["result"]["failed_count"] == 0

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    async def test_cancel_all_option_orders_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Test cancel_all_option_orders auth failure."""
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_cancel_all_option_orders,
        )

        result = await schwab_cancel_all_option_orders("acct1")
        assert result == error_response


class TestSchwabOrderOptionCreditSpread:
    """Tests for schwab_order_option_credit_spread."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_call_credit_spread_success(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test bear call credit spread order placement."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/orders/50001"}
        mock_execute.return_value = mock_response

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_option_credit_spread,
        )

        result = await schwab_order_option_credit_spread(
            "acct1",
            "CALL",
            "AAPL  251219C00150000",  # short (sell)
            "AAPL  251219C00155000",  # long (buy/hedge)
            1,
            "2.00",
        )
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["spread_type"] == "credit"
        assert result["result"]["option_type"] == "CALL"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_put_credit_spread_success(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test bull put credit spread order placement."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/orders/50002"}
        mock_execute.return_value = mock_response

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_option_credit_spread,
        )

        result = await schwab_order_option_credit_spread(
            "acct1",
            "PUT",
            "AAPL  251219P00150000",  # short (sell)
            "AAPL  251219P00145000",  # long (buy/hedge)
            1,
            "1.50",
        )
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["spread_type"] == "credit"
        assert result["result"]["option_type"] == "PUT"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_credit_spread_invalid_option_type(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test credit spread with invalid option type returns error."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_option_credit_spread,
        )

        result = await schwab_order_option_credit_spread(
            "acct1",
            "INVALID",
            "AAPL  251219C00150000",
            "AAPL  251219C00155000",
            1,
            "2.00",
        )
        assert "error" in result["result"]

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_credit_spread_api_error(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test credit spread detects API error."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Order rejected"
        mock_execute.return_value = mock_response

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_option_credit_spread,
        )

        result = await schwab_order_option_credit_spread(
            "acct1",
            "CALL",
            "AAPL  251219C00150000",
            "AAPL  251219C00155000",
            1,
            "2.00",
        )
        assert "error" in result["result"]

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    async def test_credit_spread_auth_error(self, mock_get_broker: AsyncMock) -> None:
        """Test credit spread auth failure."""
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_option_credit_spread,
        )

        result = await schwab_order_option_credit_spread(
            "acct1", "CALL", "A", "B", 1, "2.00"
        )
        assert result == error_response


class TestSchwabOrderOptionDebitSpread:
    """Tests for schwab_order_option_debit_spread."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_call_debit_spread_success(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test bull call debit spread order placement."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/orders/60001"}
        mock_execute.return_value = mock_response

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_option_debit_spread,
        )

        result = await schwab_order_option_debit_spread(
            "acct1",
            "CALL",
            "AAPL  251219C00150000",  # long (buy)
            "AAPL  251219C00155000",  # short (sell/hedge)
            1,
            "3.00",
        )
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["spread_type"] == "debit"
        assert result["result"]["option_type"] == "CALL"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_put_debit_spread_success(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test bear put debit spread order placement."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/orders/60002"}
        mock_execute.return_value = mock_response

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_option_debit_spread,
        )

        result = await schwab_order_option_debit_spread(
            "acct1",
            "PUT",
            "AAPL  251219P00155000",  # long (buy, higher strike for bear put)
            "AAPL  251219P00150000",  # short (sell/hedge)
            1,
            "2.50",
        )
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["spread_type"] == "debit"
        assert result["result"]["option_type"] == "PUT"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_debit_spread_invalid_option_type(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test debit spread with invalid option type returns error."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_option_debit_spread,
        )

        result = await schwab_order_option_debit_spread(
            "acct1",
            "STRADDLE",
            "AAPL  251219C00150000",
            "AAPL  251219C00155000",
            1,
            "3.00",
        )
        assert "error" in result["result"]

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    async def test_debit_spread_auth_error(self, mock_get_broker: AsyncMock) -> None:
        """Test debit spread auth failure."""
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        from open_stocks_mcp.tools.schwab_trading_tools import (
            schwab_order_option_debit_spread,
        )

        result = await schwab_order_option_debit_spread(
            "acct1", "CALL", "A", "B", 1, "3.00"
        )
        assert result == error_response


class TestSchwabReplaceOrder:
    """Tests for schwab_replace_order."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_replace_order_success(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful order replacement."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/orders/70001"}
        mock_execute.return_value = mock_response

        from open_stocks_mcp.tools.schwab_trading_tools import schwab_replace_order

        order_spec = {"orderType": "LIMIT", "price": "155.00"}
        result = await schwab_replace_order("acct1", "old_order_99", order_spec)
        assert result["result"]["status"] == "order_replaced"
        assert result["result"]["new_order_id"] == "70001"
        assert result["result"]["replaced_order_id"] == "old_order_99"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_trading_tools.execute_broker_request")
    async def test_replace_order_non_2xx(
        self, mock_execute: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test replace_order detects non-2xx response."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Order cannot be replaced"
        mock_execute.return_value = mock_response

        from open_stocks_mcp.tools.schwab_trading_tools import schwab_replace_order

        result = await schwab_replace_order(
            "acct1", "old_order_99", {"orderType": "LIMIT"}
        )
        assert "error" in result["result"]

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_trading_tools.get_authenticated_broker_or_error"
    )
    async def test_replace_order_auth_error(self, mock_get_broker: AsyncMock) -> None:
        """Test replace_order auth failure."""
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        from open_stocks_mcp.tools.schwab_trading_tools import schwab_replace_order

        result = await schwab_replace_order("acct1", "order99", {"orderType": "LIMIT"})
        assert result == error_response
