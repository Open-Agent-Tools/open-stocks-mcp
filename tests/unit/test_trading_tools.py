"""Unit tests for robinhood_trading_tools.py.

Focuses on the most regression-prone behaviors documented in CLAUDE.md:
- execute_with_retry is called with timeInForce='gfd' for market orders
- non_field_errors API responses are detected and returned as errors
- exception branches propagate cleanly
"""

import ast
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import robin_stocks.robinhood as rh

from open_stocks_mcp.tools.robinhood_trading_tools import (
    cancel_all_option_orders,
    cancel_all_stock_orders,
    cancel_option_order,
    cancel_stock_order,
    get_all_open_option_orders,
    get_all_open_stock_orders,
    order_buy_limit,
    order_buy_market,
    order_buy_stop_loss,
    order_sell_limit,
    order_sell_market,
    order_sell_stop_loss,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_QUOTE = [{"last_trade_price": "150.00", "symbol": "AAPL"}]
MOCK_ACCOUNT = {"buying_power": "10000.00"}
MOCK_POSITION = [{"symbol": "AAPL", "quantity": "10"}]
MOCK_ORDER = {
    "id": "order-001",
    "state": "confirmed",
    "created_at": "2024-01-01T00:00:00Z",
}


def assert_decorator_error_response(
    result: dict[str, dict[str, object]], function_name: str
) -> None:
    """Assert unexpected exceptions are handled by the shared decorator."""
    payload = result["result"]
    assert payload["status"] == "error"
    assert "error_type" in payload
    assert payload["context"] == f"in {function_name}"


def _returns_create_success_error_response(handler: ast.ExceptHandler) -> bool:
    for node in ast.walk(handler):
        if not isinstance(node, ast.Return):
            continue
        value = node.value
        if not (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "create_success_response"
            and value.args
            and isinstance(value.args[0], ast.Dict)
        ):
            continue

        keys = {
            key.value
            for key in value.args[0].keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        if {"error", "status"} <= keys:
            return True
    return False


def test_trading_tools_do_not_keep_local_exception_response_boilerplate() -> None:
    module_path = (
        Path(__file__).parents[2]
        / "src"
        / "open_stocks_mcp"
        / "tools"
        / "robinhood_trading_tools.py"
    )
    tree = ast.parse(module_path.read_text())

    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if not (
            isinstance(node.type, ast.Name)
            and node.type.id == "Exception"
            and _returns_create_success_error_response(node)
        ):
            continue
        offenders.append(node.lineno)

    assert offenders == []


# ---------------------------------------------------------------------------
# order_buy_market
# ---------------------------------------------------------------------------


class TestOrderBuyMarket:
    """Tests for order_buy_market."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_success_passes_timeinforce_gfd(
        self, mock_execute: AsyncMock
    ) -> None:
        """Market buy order passes timeInForce='gfd' to execute_with_retry."""
        mock_execute.side_effect = [MOCK_QUOTE, MOCK_ACCOUNT, MOCK_ORDER]

        result = await order_buy_market("AAPL", 5)

        assert result["result"]["status"] == "success"
        assert result["result"]["order_id"] == "order-001"
        assert result["result"]["side"] == "buy"
        assert result["result"]["order_type"] == "market"

        # The third call must pass rh.order_buy_market as the callable with the
        # correct symbol/quantity positional args and timeInForce='gfd' kwarg.
        order_call = mock_execute.call_args_list[2]
        assert order_call.args[0] is rh.order_buy_market
        assert order_call.args[1] == "AAPL"
        assert order_call.args[2] == 5
        assert order_call.kwargs.get("timeInForce") == "gfd"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_non_field_errors_returned_as_error(
        self, mock_execute: AsyncMock
    ) -> None:
        """When API returns non_field_errors, result contains error status."""
        api_error = {"non_field_errors": ["Insufficient shares available"]}
        mock_execute.side_effect = [MOCK_QUOTE, MOCK_ACCOUNT, api_error]

        result = await order_buy_market("AAPL", 5)

        assert "error" in result["result"]
        assert "Insufficient shares available" in result["result"]["error"]
        assert result["result"]["status"] == "error"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_order_placement_exception(self, mock_execute: AsyncMock) -> None:
        """Exception during order placement returns decorator error response."""
        mock_execute.side_effect = [
            MOCK_QUOTE,
            MOCK_ACCOUNT,
            Exception("Network error"),
        ]

        result = await order_buy_market("AAPL", 5)

        assert_decorator_error_response(result, "order_buy_market")

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_symbol_returns_error(self) -> None:
        """Empty symbol fails validation before any API call."""
        result = await order_buy_market("", 5)

        assert result["result"]["status"] == "error"
        assert "symbol" in result["result"]["error"].lower()

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_quantity_returns_error(self) -> None:
        """Non-positive quantity fails validation before any API call."""
        result = await order_buy_market("AAPL", 0)

        assert result["result"]["status"] == "error"
        assert "quantity" in result["result"]["error"].lower()

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_symbol_not_found_returns_error(
        self, mock_execute: AsyncMock
    ) -> None:
        """Quote lookup returning empty list yields a symbol-not-found error."""
        mock_execute.return_value = [{}]  # no last_trade_price

        result = await order_buy_market("FAKE", 1)

        assert result["result"]["status"] == "error"
        assert "not found" in result["result"]["error"]

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_insufficient_buying_power_returns_error(
        self, mock_execute: AsyncMock
    ) -> None:
        """Insufficient buying power returns an error without placing an order."""
        mock_execute.side_effect = [
            MOCK_QUOTE,
            {"buying_power": "1.00"},  # way too low
        ]

        result = await order_buy_market("AAPL", 100)

        assert result["result"]["status"] == "error"
        assert "buying power" in result["result"]["error"].lower()
        # Ensure the order was NOT placed (only 2 calls made)
        assert mock_execute.call_count == 2


# ---------------------------------------------------------------------------
# order_sell_market
# ---------------------------------------------------------------------------


class TestOrderSellMarket:
    """Tests for order_sell_market."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_success_passes_timeinforce_gfd(
        self, mock_execute: AsyncMock
    ) -> None:
        """Market sell order passes timeInForce='gfd' to execute_with_retry."""
        mock_execute.side_effect = [MOCK_POSITION, MOCK_ORDER]

        result = await order_sell_market("AAPL", 5)

        assert result["result"]["status"] == "success"
        assert result["result"]["side"] == "sell"
        assert result["result"]["order_type"] == "market"

        # Second call (order placement) must pass rh.order_sell_market as the
        # callable with the correct symbol/quantity positional args and
        # timeInForce='gfd' kwarg.
        order_call = mock_execute.call_args_list[1]
        assert order_call.args[0] is rh.order_sell_market
        assert order_call.args[1] == "AAPL"
        assert order_call.args[2] == 5
        assert order_call.kwargs.get("timeInForce") == "gfd"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_non_field_errors_returned_as_error(
        self, mock_execute: AsyncMock
    ) -> None:
        """When API returns non_field_errors, result contains error status."""
        api_error = {"non_field_errors": ["Market is closed"]}
        mock_execute.side_effect = [MOCK_POSITION, api_error]

        result = await order_sell_market("AAPL", 5)

        assert "error" in result["result"]
        assert "Market is closed" in result["result"]["error"]
        assert result["result"]["status"] == "error"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_order_placement_exception(self, mock_execute: AsyncMock) -> None:
        """Exception during order placement returns decorator error response."""
        mock_execute.side_effect = [MOCK_POSITION, Exception("Timeout")]

        result = await order_sell_market("AAPL", 5)

        assert_decorator_error_response(result, "order_sell_market")

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_symbol_returns_error(self) -> None:
        """Empty symbol fails validation before any API call."""
        result = await order_sell_market("", 5)

        assert result["result"]["status"] == "error"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_quantity_returns_error(self) -> None:
        """Zero quantity fails validation before any API call."""
        result = await order_sell_market("AAPL", -1)

        assert result["result"]["status"] == "error"
        assert "quantity" in result["result"]["error"].lower()

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_no_position_returns_error(self, mock_execute: AsyncMock) -> None:
        """Selling with no open position returns error without placing order."""
        mock_execute.return_value = []  # empty positions

        result = await order_sell_market("AAPL", 5)

        assert result["result"]["status"] == "error"
        assert "position" in result["result"]["error"].lower()
        assert mock_execute.call_count == 1

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_insufficient_shares_returns_error(
        self, mock_execute: AsyncMock
    ) -> None:
        """Trying to sell more shares than owned returns error."""
        mock_execute.return_value = [{"symbol": "AAPL", "quantity": "2"}]

        result = await order_sell_market("AAPL", 10)

        assert result["result"]["status"] == "error"
        assert "shares" in result["result"]["error"].lower()


# ---------------------------------------------------------------------------
# order_buy_limit
# ---------------------------------------------------------------------------


class TestOrderBuyLimit:
    """Tests for order_buy_limit."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_success(self, mock_execute: AsyncMock) -> None:
        """Limit buy order succeeds with valid inputs."""
        mock_execute.side_effect = [MOCK_QUOTE, MOCK_ACCOUNT, MOCK_ORDER]

        result = await order_buy_limit("AAPL", 5, 140.00)

        assert result["result"]["status"] == "success"
        assert result["result"]["order_type"] == "limit"
        assert result["result"]["side"] == "buy"
        assert result["result"]["price"] == 140.00

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_limit_price_returns_error(self) -> None:
        """Non-positive limit price fails validation."""
        result = await order_buy_limit("AAPL", 5, -10.0)

        assert result["result"]["status"] == "error"
        assert "limit price" in result["result"]["error"].lower()

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_zero_quantity_returns_error(self) -> None:
        """Zero quantity fails validation."""
        result = await order_buy_limit("AAPL", 0, 140.0)

        assert result["result"]["status"] == "error"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_limit_price_too_high_returns_error(
        self, mock_execute: AsyncMock
    ) -> None:
        """Limit price >150% of current price is rejected before placing order."""
        mock_execute.return_value = [{"last_trade_price": "100.00"}]

        result = await order_buy_limit("AAPL", 5, 200.00)  # >150% of 100

        assert result["result"]["status"] == "error"
        assert "too high" in result["result"]["error"].lower()
        assert mock_execute.call_count == 1  # only quote lookup, no order placed

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_non_field_errors_returned_as_error(
        self, mock_execute: AsyncMock
    ) -> None:
        """non_field_errors from limit buy API response are surfaced as errors."""
        api_error = {"non_field_errors": ["Invalid limit price"]}
        mock_execute.side_effect = [MOCK_QUOTE, MOCK_ACCOUNT, api_error]

        result = await order_buy_limit("AAPL", 5, 140.00)

        assert "error" in result["result"]
        assert "Invalid limit price" in result["result"]["error"]
        assert result["result"]["status"] == "error"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_order_placement_exception(self, mock_execute: AsyncMock) -> None:
        """Exception during limit order placement returns decorator error."""
        mock_execute.side_effect = [MOCK_QUOTE, MOCK_ACCOUNT, Exception("API down")]

        result = await order_buy_limit("AAPL", 5, 140.00)

        assert_decorator_error_response(result, "order_buy_limit")


# ---------------------------------------------------------------------------
# order_sell_limit
# ---------------------------------------------------------------------------


class TestOrderSellLimit:
    """Tests for order_sell_limit."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_success(self, mock_execute: AsyncMock) -> None:
        """Limit sell order succeeds with valid inputs."""
        mock_execute.side_effect = [MOCK_POSITION, MOCK_ORDER]

        result = await order_sell_limit("AAPL", 5, 160.00)

        assert result["result"]["status"] == "success"
        assert result["result"]["order_type"] == "limit"
        assert result["result"]["side"] == "sell"
        assert result["result"]["price"] == 160.00

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_limit_price_returns_error(self) -> None:
        """Non-positive limit price fails validation."""
        result = await order_sell_limit("AAPL", 5, 0.0)

        assert result["result"]["status"] == "error"
        assert "limit price" in result["result"]["error"].lower()

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_no_position_returns_error(self, mock_execute: AsyncMock) -> None:
        """Limit sell with no open position returns error."""
        mock_execute.return_value = []

        result = await order_sell_limit("AAPL", 5, 160.00)

        assert result["result"]["status"] == "error"
        assert "position" in result["result"]["error"].lower()

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_non_field_errors_returned_as_error(
        self, mock_execute: AsyncMock
    ) -> None:
        """non_field_errors from limit sell API response are surfaced."""
        api_error = {"non_field_errors": ["Order rejected by exchange"]}
        mock_execute.side_effect = [MOCK_POSITION, api_error]

        result = await order_sell_limit("AAPL", 5, 160.00)

        assert "error" in result["result"]
        assert "Order rejected by exchange" in result["result"]["error"]

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_order_placement_exception(self, mock_execute: AsyncMock) -> None:
        """Exception during limit sell placement returns decorator error."""
        mock_execute.side_effect = [MOCK_POSITION, Exception("Connection reset")]

        result = await order_sell_limit("AAPL", 5, 160.00)

        assert_decorator_error_response(result, "order_sell_limit")


# ---------------------------------------------------------------------------
# order_buy_stop_loss / order_sell_stop_loss
# ---------------------------------------------------------------------------


class TestOrderStopLoss:
    """Smoke tests for stop loss orders."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_buy_stop_loss_invalid_stop_price(self) -> None:
        """Non-positive stop price fails validation."""
        result = await order_buy_stop_loss("AAPL", 5, 0.0)

        assert result["result"]["status"] == "error"
        assert "stop price" in result["result"]["error"].lower()

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_buy_stop_loss_below_current_price_rejected(
        self, mock_execute: AsyncMock
    ) -> None:
        """Stop buy price below current market price is rejected."""
        mock_execute.return_value = [{"last_trade_price": "150.00"}]

        result = await order_buy_stop_loss("AAPL", 5, 100.00)  # below current

        assert result["result"]["status"] == "error"
        assert "above" in result["result"]["error"].lower()

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_buy_stop_loss_success(self, mock_execute: AsyncMock) -> None:
        """Valid stop buy order succeeds."""
        mock_execute.side_effect = [
            [{"last_trade_price": "100.00"}],  # quote (stop must be above)
            MOCK_ORDER,
        ]

        result = await order_buy_stop_loss("AAPL", 5, 120.00)

        assert result["result"]["status"] == "success"
        assert result["result"]["order_type"] == "stop_loss"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sell_stop_loss_invalid_quantity(self) -> None:
        """Non-positive quantity fails validation for stop sell."""
        result = await order_sell_stop_loss("AAPL", 0, 100.00)

        assert result["result"]["status"] == "error"


# ---------------------------------------------------------------------------
# cancel_stock_order
# ---------------------------------------------------------------------------


class TestCancelStockOrder:
    """Tests for cancel_stock_order."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_order_id_returns_error(self) -> None:
        """Empty order_id fails validation."""
        result = await cancel_stock_order("")

        assert result["result"]["status"] == "error"
        assert "order_id" in result["result"]["error"].lower()

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_cancel_success(self, mock_execute: AsyncMock) -> None:
        """Valid cancel returns status='cancelled'."""
        mock_execute.return_value = {"updated_at": "2024-01-01T01:00:00Z"}

        result = await cancel_stock_order("order-001")

        assert result["result"]["status"] == "cancelled"
        assert result["result"]["order_id"] == "order-001"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_cancel_returns_none_is_error(self, mock_execute: AsyncMock) -> None:
        """API returning None for cancel is treated as failure."""
        mock_execute.return_value = None

        result = await cancel_stock_order("order-001")

        assert result["result"]["status"] == "error"


# ---------------------------------------------------------------------------
# cancel_option_order
# ---------------------------------------------------------------------------


class TestCancelOptionOrder:
    """Tests for cancel_option_order."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_order_id_returns_error(self) -> None:
        """Empty order_id fails validation."""
        result = await cancel_option_order("")

        assert result["result"]["status"] == "error"

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_cancel_success(self, mock_execute: AsyncMock) -> None:
        """Valid cancel option order returns status='cancelled'."""
        mock_execute.return_value = {"updated_at": "2024-01-01T01:00:00Z"}

        result = await cancel_option_order("opt-order-001")

        assert result["result"]["status"] == "cancelled"


# ---------------------------------------------------------------------------
# cancel_all_stock_orders
# ---------------------------------------------------------------------------


class TestCancelAllStockOrders:
    """Tests for cancel_all_stock_orders."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_no_open_orders(self, mock_execute: AsyncMock) -> None:
        """No open orders returns zero cancelled count."""
        mock_execute.return_value = []

        result = await cancel_all_stock_orders()

        assert result["result"]["cancelled_count"] == 0

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_cancels_multiple_orders(self, mock_execute: AsyncMock) -> None:
        """All open orders are cancelled and count is correct."""
        open_orders = [{"id": "o1"}, {"id": "o2"}, {"id": "o3"}]
        # First call fetches open orders, subsequent calls cancel them
        mock_execute.side_effect = [open_orders, None, None, None]

        result = await cancel_all_stock_orders()

        assert result["result"]["cancelled_count"] == 3
        assert result["result"]["total_orders"] == 3

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_fetch_exception_returns_error(self, mock_execute: AsyncMock) -> None:
        """Exception while fetching open orders returns decorator error."""
        mock_execute.side_effect = Exception("Auth expired")

        result = await cancel_all_stock_orders()

        assert_decorator_error_response(result, "cancel_all_stock_orders")


# ---------------------------------------------------------------------------
# cancel_all_option_orders
# ---------------------------------------------------------------------------


class TestCancelAllOptionOrders:
    """Tests for cancel_all_option_orders."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_no_open_option_orders(self, mock_execute: AsyncMock) -> None:
        """No open option orders returns zero cancelled count."""
        mock_execute.return_value = []

        result = await cancel_all_option_orders()

        assert result["result"]["cancelled_count"] == 0

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_cancels_multiple_option_orders(
        self, mock_execute: AsyncMock
    ) -> None:
        """All open option orders are cancelled."""
        open_orders = [{"id": "opt1"}, {"id": "opt2"}]
        mock_execute.side_effect = [open_orders, None, None]

        result = await cancel_all_option_orders()

        assert result["result"]["cancelled_count"] == 2


# ---------------------------------------------------------------------------
# get_all_open_stock_orders / get_all_open_option_orders
# ---------------------------------------------------------------------------


class TestGetOpenOrders:
    """Tests for get_all_open_stock_orders and get_all_open_option_orders."""

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_get_stock_orders_success(self, mock_execute: AsyncMock) -> None:
        """Returns list of open stock orders."""
        open_orders = [{"id": "o1", "state": "queued"}, {"id": "o2", "state": "queued"}]
        mock_execute.return_value = open_orders

        result = await get_all_open_stock_orders()

        assert "result" in result
        assert isinstance(result["result"], dict)

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_get_stock_orders_empty(self, mock_execute: AsyncMock) -> None:
        """Empty open orders list returns a result without error."""
        mock_execute.return_value = []

        result = await get_all_open_stock_orders()

        assert "result" in result

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_get_stock_orders_fetch_exception_returns_error(
        self, mock_execute: AsyncMock
    ) -> None:
        """Exception while fetching stock orders returns decorator error."""
        mock_execute.side_effect = Exception("Service unavailable")

        result = await get_all_open_stock_orders()

        assert_decorator_error_response(result, "get_all_open_stock_orders")

    @pytest.mark.journey_trading
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.robinhood_trading_tools.execute_with_retry")
    async def test_get_option_orders_success(self, mock_execute: AsyncMock) -> None:
        """Returns list of open option orders."""
        mock_execute.return_value = [{"id": "opt1"}]

        result = await get_all_open_option_orders()

        assert "result" in result
