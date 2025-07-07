"""Tests for robinhood_order_tools module."""

import pytest

from open_stocks_mcp.tools.robinhood_order_tools import (
    get_options_orders,
    get_stock_orders,
)


class TestStockOrders:
    """Test stock_orders tool."""

    @pytest.mark.asyncio
    async def test_get_stock_orders_success(self, mocker):
        """Test successful stock orders retrieval."""
        mock_orders = [
            {
                "instrument": "test-instrument-url",
                "side": "buy",
                "quantity": "10.00000000",
                "average_price": "100.00",
                "state": "filled",
                "created_at": "2023-01-01T00:00:00Z",
            }
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_stock_orders",
            return_value=mock_orders,
        )
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_order_tools.rh.get_symbol_by_url",
            return_value="AAPL",
        )
        result = await get_stock_orders()

        assert result["result"]["count"] == 1
        assert result["result"]["orders"][0]["symbol"] == "AAPL"
        assert result["result"]["orders"][0]["side"] == "BUY"
        assert result["result"]["orders"][0]["quantity"] == "10.00000000"
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_stock_orders_empty(self, mocker):
        """Test stock orders retrieval with no orders."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_stock_orders",
            return_value=[],
        )
        result = await get_stock_orders()

        assert result["result"]["orders"] == []
        assert result["result"]["message"] == "No recent stock orders found."
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_stock_orders_exception(self, mocker):
        """Test stock orders retrieval with exception."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_stock_orders",
            side_effect=Exception("Orders Error"),
        )
        result = await get_stock_orders()

        assert "Orders Error" in result["result"]["error"]
        assert result["result"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_get_stock_orders_with_missing_instrument(self, mocker):
        """Test stock orders with missing instrument URL."""
        mock_orders = [
            {
                "instrument": None,  # Missing instrument URL
                "side": "buy",
                "quantity": "10.00000000",
                "average_price": "100.00",
                "state": "filled",
                "created_at": "2023-01-01T00:00:00Z",
            }
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_stock_orders",
            return_value=mock_orders,
        )
        result = await get_stock_orders()

        assert result["result"]["count"] == 1
        assert result["result"]["orders"][0]["symbol"] == "N/A"
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_stock_orders_with_last_transaction_at(self, mocker):
        """Test stock orders uses last_transaction_at over created_at."""
        mock_orders = [
            {
                "instrument": "test-instrument-url",
                "side": "buy",
                "quantity": "10.00000000",
                "average_price": "100.00",
                "state": "filled",
                "created_at": "2023-01-01T00:00:00Z",
                "last_transaction_at": "2023-01-02T00:00:00Z",  # Should use this
            }
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_stock_orders",
            return_value=mock_orders,
        )
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_order_tools.rh.get_symbol_by_url",
            return_value="AAPL",
        )
        result = await get_stock_orders()

        assert result["result"]["orders"][0]["created_at"] == "2023-01-02T00:00:00Z"
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_stock_orders_limits_to_five(self, mocker):
        """Test stock orders limits results to 5 most recent."""
        mock_orders = [
            {
                "instrument": "test-instrument-url",
                "side": "buy",
                "quantity": "10.00000000",
                "average_price": "100.00",
                "state": "filled",
                "created_at": f"2023-01-0{i}T00:00:00Z",
            }
            for i in range(1, 8)  # 7 orders
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_stock_orders",
            return_value=mock_orders,
        )
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_order_tools.rh.get_symbol_by_url",
            return_value="AAPL",
        )
        result = await get_stock_orders()

        assert result["result"]["count"] == 5  # Limited to 5
        assert result["result"]["status"] == "success"


class TestOptionsOrders:
    """Test options_orders tool."""

    @pytest.mark.asyncio
    async def test_get_options_orders_not_implemented(self, mocker):
        """Test options orders returns not implemented."""
        # Mock to simulate function not available/not implemented
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_option_orders",
            side_effect=Exception("not implemented"),
        )
        result = await get_options_orders()

        assert (
            result["result"]["message"]
            == "Options orders retrieval not yet implemented or not available. Coming soon!"
        )
        # Check the inner status field that indicates not_implemented
        assert "not_implemented" in str(result["result"])
        assert result["result"]["orders"] == []
        assert result["result"]["count"] == 0

    @pytest.mark.asyncio
    async def test_get_options_orders_with_exception(self, mocker):
        """Test options orders handles exceptions gracefully."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_order_tools.logger.info",
            side_effect=Exception("Logger Error"),
        )
        result = await get_options_orders()

        assert "Logger Error" in result["result"]["error"]
        assert result["result"]["status"] == "error"
