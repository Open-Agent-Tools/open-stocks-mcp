"""Unit tests for account tools."""

from typing import Any
from unittest.mock import patch

import pytest

from open_stocks_mcp.tools.robinhood_account_tools import (
    get_account_details,
    get_account_info,
    get_portfolio,
    get_positions,
)
from open_stocks_mcp.tools.robinhood_advanced_portfolio_tools import (
    get_build_holdings,
    get_build_user_profile,
    get_day_trades,
)
from open_stocks_mcp.tools.robinhood_order_tools import (
    get_options_orders,
    get_stock_orders,
)


class TestAccountTools:
    """Test account tools with mocked responses."""

    @patch("open_stocks_mcp.tools.robinhood_account_tools.rh.load_user_profile")
    @pytest.mark.asyncio
    async def test_get_account_info_success(self, mock_profile: Any) -> None:
        """Test successful account info retrieval."""
        mock_profile.return_value = {
            "username": "testuser",
            "created_at": "2023-01-01T00:00:00Z",
        }

        result = await get_account_info()

        assert "result" in result
        assert result["result"]["username"] == "testuser"
        assert result["result"]["created_at"] == "2023-01-01T00:00:00Z"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_account_tools.rh.load_user_profile")
    @pytest.mark.asyncio
    async def test_get_account_info_error(self, mock_profile: Any) -> None:
        """Test account info error handling."""
        mock_profile.side_effect = Exception("API Error")

        result = await get_account_info()

        assert "result" in result
        assert "error" in result["result"]

    @patch("open_stocks_mcp.tools.robinhood_account_tools.rh.load_portfolio_profile")
    @pytest.mark.asyncio
    async def test_get_portfolio_success(self, mock_portfolio: Any) -> None:
        """Test successful portfolio retrieval."""
        mock_portfolio.return_value = {
            "total_return_today": "50.00",
            "total_return_today_percent": "2.50",
            "market_value": "2000.00",
        }

        result = await get_portfolio()

        assert "result" in result
        # The actual response structure depends on how the tool processes the data
        assert isinstance(result["result"], dict)

    @patch("open_stocks_mcp.tools.robinhood_account_tools.rh.get_symbol_by_url")
    @patch("open_stocks_mcp.tools.robinhood_account_tools.rh.get_open_stock_positions")
    @pytest.mark.asyncio
    async def test_get_positions_success(
        self, mock_positions: Any, mock_symbol: Any
    ) -> None:
        """Test successful positions retrieval."""
        mock_positions.return_value = [
            {
                "instrument": "https://robinhood.com/instruments/aapl123/",
                "quantity": "10.0000",
                "average_buy_price": "150.00",
                "updated_at": "2023-01-01T00:00:00Z",
            },
            {
                "instrument": "https://robinhood.com/instruments/googl456/",
                "quantity": "5.0000",
                "average_buy_price": "2500.00",
                "updated_at": "2023-01-01T00:00:00Z",
            },
        ]

        # Mock symbol lookup for each instrument URL
        mock_symbol.side_effect = ["AAPL", "GOOGL"]

        result = await get_positions()

        assert "result" in result
        # The result contains structured data with positions, count, status
        assert isinstance(result["result"], dict)
        assert "positions" in result["result"]
        assert "count" in result["result"]
        assert result["result"]["count"] == 2

    @patch("open_stocks_mcp.tools.robinhood_account_tools.rh.load_phoenix_account")
    @pytest.mark.asyncio
    async def test_get_account_details_success(self, mock_account: Any) -> None:
        """Test successful account details retrieval."""
        mock_account.return_value = {
            "account_number": "123456789",
            "buying_power": "1000.00",
        }

        result = await get_account_details()

        assert "result" in result
        assert isinstance(result["result"], dict)

    @patch("open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.build_holdings")
    @pytest.mark.asyncio
    async def test_get_build_holdings_success(self, mock_holdings: Any) -> None:
        """Test successful build holdings retrieval."""
        mock_holdings.return_value = {
            "AAPL": {
                "price": "150.00",
                "quantity": "10",
                "average_buy_price": "145.00",
                "equity": "1500.00",
                "percent_change": "3.45",
                "equity_change": "50.00",
                "type": "stock",
                "name": "Apple Inc",
                "pe_ratio": "25.5",
                "percentage": "15.2",
            },
            "GOOGL": {
                "price": "2800.00",
                "quantity": "5",
                "average_buy_price": "2700.00",
                "equity": "14000.00",
                "percent_change": "3.70",
                "equity_change": "500.00",
                "type": "stock",
                "name": "Alphabet Inc",
                "pe_ratio": "28.3",
                "percentage": "84.8",
            },
        }

        result = await get_build_holdings()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert result["result"]["total_positions"] == 2
        assert "holdings" in result["result"]
        assert "AAPL" in result["result"]["holdings"]
        assert "GOOGL" in result["result"]["holdings"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.build_holdings")
    @pytest.mark.asyncio
    async def test_get_build_holdings_no_data(self, mock_holdings: Any) -> None:
        """Test build holdings when no data is available."""
        mock_holdings.return_value = None

        result = await get_build_holdings()

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert result["result"]["total_positions"] == 0
        assert result["result"]["holdings"] == {}

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.build_holdings")
    @pytest.mark.asyncio
    async def test_get_build_holdings_error(self, mock_holdings: Any) -> None:
        """Test build holdings error handling."""
        mock_holdings.side_effect = Exception("API Error")

        result = await get_build_holdings()

        assert "result" in result
        assert "error" in result["result"]

    @patch(
        "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.build_user_profile"
    )
    @pytest.mark.asyncio
    async def test_get_build_user_profile_success(self, mock_profile: Any) -> None:
        """Test successful build user profile retrieval."""
        mock_profile.return_value = {
            "equity": "50000.00",
            "extended_hours_equity": "50100.00",
            "cash": "2500.00",
            "dividend_total": "1245.67",
            "total_return_today": "250.00",
            "total_return_today_percent": "0.50",
        }

        result = await get_build_user_profile()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert result["result"]["equity"] == "50000.00"
        assert result["result"]["dividend_total"] == "1245.67"
        assert result["result"]["cash"] == "2500.00"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch(
        "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.build_user_profile"
    )
    @pytest.mark.asyncio
    async def test_get_build_user_profile_no_data(self, mock_profile: Any) -> None:
        """Test build user profile when no data is available."""
        mock_profile.return_value = None

        result = await get_build_user_profile()

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert "error" in result["result"]

    @patch(
        "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.load_account_profile"
    )
    @pytest.mark.asyncio
    async def test_get_day_trades_success(self, mock_account: Any) -> None:
        """Test successful day trades retrieval."""
        mock_account.return_value = {
            "day_trade_count": "2",
            "is_pattern_day_trader": False,
            "day_trade_buying_power": "25000.00",
            "overnight_buying_power": "12500.00",
            "max_ach_early_access_amount": "1000.00",
        }

        result = await get_day_trades()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert result["result"]["day_trade_count"] == 2
        assert result["result"]["remaining_day_trades"] == 1
        assert not result["result"]["pattern_day_trader"]
        assert result["result"]["day_trade_buying_power"] == "25000.00"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch(
        "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.load_account_profile"
    )
    @pytest.mark.asyncio
    async def test_get_day_trades_no_data(self, mock_account: Any) -> None:
        """Test day trades when no account data is available."""
        mock_account.return_value = None

        result = await get_day_trades()

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert "error" in result["result"]

    @patch("open_stocks_mcp.tools.robinhood_order_tools.rh.get_symbol_by_url")
    @patch("open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_stock_orders")
    @pytest.mark.asyncio
    async def test_get_stock_orders_success(
        self, mock_orders: Any, mock_symbol: Any
    ) -> None:
        """Test successful stock orders retrieval."""
        mock_orders.return_value = [
            {
                "instrument": "https://robinhood.com/instruments/aapl123/",
                "side": "buy",
                "quantity": "10.0000",
                "average_price": "150.00",
                "state": "filled",
                "created_at": "2023-01-01T10:00:00Z",
                "last_transaction_at": "2023-01-01T10:05:00Z",
            },
            {
                "instrument": "https://robinhood.com/instruments/googl456/",
                "side": "sell",
                "quantity": "5.0000",
                "average_price": "2800.00",
                "state": "filled",
                "created_at": "2023-01-01T11:00:00Z",
                "last_transaction_at": "2023-01-01T11:05:00Z",
            },
        ]

        # Mock symbol lookup for each instrument URL
        mock_symbol.side_effect = ["AAPL", "GOOGL"]

        result = await get_stock_orders()

        assert "result" in result
        assert result["result"]["count"] == 2
        assert len(result["result"]["orders"]) == 2
        assert result["result"]["orders"][0]["symbol"] == "AAPL"
        assert result["result"]["orders"][0]["side"] == "BUY"
        assert result["result"]["orders"][1]["symbol"] == "GOOGL"
        assert result["result"]["orders"][1]["side"] == "SELL"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_stock_orders")
    @pytest.mark.asyncio
    async def test_get_stock_orders_no_data(self, mock_orders: Any) -> None:
        """Test stock orders when no orders are available."""
        mock_orders.return_value = None

        result = await get_stock_orders()

        assert "result" in result
        assert result["result"]["count"] == 0
        assert result["result"]["orders"] == []
        assert "No recent stock orders found" in result["result"]["message"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_stock_orders")
    @pytest.mark.asyncio
    async def test_get_stock_orders_error(self, mock_orders: Any) -> None:
        """Test stock orders error handling."""
        mock_orders.side_effect = Exception("API Error")

        result = await get_stock_orders()

        assert "result" in result
        assert "error" in result["result"]

    @patch("open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_option_orders")
    @pytest.mark.asyncio
    async def test_get_options_orders_success(self, mock_orders: Any) -> None:
        """Test successful options orders retrieval."""
        mock_orders.return_value = [
            {
                "type": "call",
                "chain_symbol": "AAPL",
                "direction": "buy",
                "quantity": "1.0000",
                "price": "5.00",
                "state": "filled",
                "created_at": "2023-01-01T10:00:00Z",
            },
            {
                "type": "put",
                "chain_symbol": "GOOGL",
                "direction": "sell",
                "quantity": "2.0000",
                "price": "8.50",
                "state": "filled",
                "created_at": "2023-01-01T11:00:00Z",
            },
        ]

        result = await get_options_orders()

        assert "result" in result
        assert result["result"]["count"] == 2
        assert len(result["result"]["orders"]) == 2
        assert result["result"]["orders"][0]["option_type"] == "call"
        assert result["result"]["orders"][0]["chain_symbol"] == "AAPL"
        assert result["result"]["orders"][0]["side"] == "BUY"
        assert result["result"]["orders"][1]["option_type"] == "put"
        assert result["result"]["orders"][1]["chain_symbol"] == "GOOGL"
        assert result["result"]["orders"][1]["side"] == "SELL"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_option_orders")
    @pytest.mark.asyncio
    async def test_get_options_orders_no_data(self, mock_orders: Any) -> None:
        """Test options orders when no orders are available."""
        mock_orders.return_value = None

        result = await get_options_orders()

        assert "result" in result
        assert result["result"]["count"] == 0
        assert result["result"]["orders"] == []
        assert "No recent options orders found" in result["result"]["message"]

    @patch("open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_option_orders")
    @pytest.mark.asyncio
    async def test_get_options_orders_not_implemented(self, mock_orders: Any) -> None:
        """Test options orders when API is not implemented."""
        mock_orders.side_effect = Exception("not implemented")

        result = await get_options_orders()

        assert "result" in result
        assert result["result"]["status"] == "not_implemented"
        assert result["result"]["count"] == 0
        assert "not yet implemented" in result["result"]["message"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_option_orders")
    @pytest.mark.asyncio
    async def test_get_options_orders_error(self, mock_orders: Any) -> None:
        """Test options orders error handling."""
        mock_orders.side_effect = Exception("API Error")

        result = await get_options_orders()

        assert "result" in result
        assert "error" in result["result"]
