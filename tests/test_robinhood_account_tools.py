"""Tests for robinhood_account_tools module."""

import pytest

from open_stocks_mcp.tools.robinhood_account_tools import (
    get_account_details,
    get_account_info,
    get_portfolio,
    get_portfolio_history,
    get_positions,
)


class TestAccountInfo:
    """Test account_info tool."""

    @pytest.mark.asyncio
    async def test_get_account_info_success(self, mocker):
        """Test successful account info retrieval."""
        mock_profile = {"username": "testuser", "created_at": "2023-01-01T00:00:00Z"}

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.load_user_profile",
            return_value=mock_profile,
        )
        result = await get_account_info()

        assert result["result"]["username"] == "testuser"
        assert result["result"]["created_at"] == "2023-01-01T00:00:00Z"
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_account_info_exception(self, mocker):
        """Test account info retrieval with exception."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.load_user_profile",
            side_effect=Exception("API Error"),
        )
        result = await get_account_info()

        assert "API Error" in result["result"]["error"]
        assert result["result"]["status"] == "error"


class TestPortfolio:
    """Test portfolio tool."""

    @pytest.mark.asyncio
    async def test_get_portfolio_success(self, mocker):
        """Test successful portfolio retrieval."""
        mock_portfolio = {
            "market_value": "1000.00",
            "equity": "1050.00",
            "buying_power": "500.00",
        }

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.load_portfolio_profile",
            return_value=mock_portfolio,
        )
        result = await get_portfolio()

        assert result["result"]["market_value"] == "1000.00"
        assert result["result"]["equity"] == "1050.00"
        assert result["result"]["buying_power"] == "500.00"
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_portfolio_exception(self, mocker):
        """Test portfolio retrieval with exception."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.load_portfolio_profile",
            side_effect=Exception("Portfolio Error"),
        )
        result = await get_portfolio()

        assert "Portfolio Error" in result["result"]["error"]
        assert result["result"]["status"] == "error"


class TestAccountDetails:
    """Test account_details tool."""

    @pytest.mark.asyncio
    async def test_get_account_details_success(self, mocker):
        """Test successful account details retrieval."""
        mock_account_data = {
            "portfolio_equity": "1000.00",
            "total_equity": "1000.00",
            "account_buying_power": "500.00",
            "options_buying_power": "500.00",
            "crypto_buying_power": "500.00",
            "uninvested_cash": "200.00",
            "withdrawable_cash": "200.00",
            "cash_available_from_instant_deposits": "0.00",
            "cash_held_for_orders": "0.00",
            "near_margin_call": False,
        }

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.load_phoenix_account",
            return_value=mock_account_data,
        )
        result = await get_account_details()

        assert result["result"]["portfolio_equity"] == "1000.00"
        assert result["result"]["total_equity"] == "1000.00"
        assert result["result"]["account_buying_power"] == "500.00"
        assert not result["result"]["near_margin_call"]
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_account_details_no_data(self, mocker):
        """Test account details retrieval with no data."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.load_phoenix_account",
            return_value=None,
        )
        result = await get_account_details()

        assert result["result"]["message"] == "No account data found"
        assert result["result"]["status"] == "no_data"

    @pytest.mark.asyncio
    async def test_get_account_details_exception(self, mocker):
        """Test account details retrieval with exception."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.load_phoenix_account",
            side_effect=Exception("Account Details Error"),
        )
        result = await get_account_details()

        assert "Account Details Error" in result["result"]["error"]
        assert result["result"]["status"] == "error"


class TestPositions:
    """Test positions tool."""

    @pytest.mark.asyncio
    async def test_get_positions_success(self, mocker):
        """Test successful positions retrieval."""
        mock_positions = [
            {
                "instrument": "test-instrument-url",
                "quantity": "10.00000000",
                "average_buy_price": "100.00",
                "updated_at": "2023-01-01T00:00:00Z",
            }
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.get_open_stock_positions",
            return_value=mock_positions,
        )
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.get_symbol_by_url",
            return_value="AAPL",
        )
        result = await get_positions()

        assert result["result"]["count"] == 1
        assert result["result"]["positions"][0]["symbol"] == "AAPL"
        assert result["result"]["positions"][0]["quantity"] == "10.00000000"
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_positions_empty(self, mocker):
        """Test positions retrieval with no positions."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.get_open_stock_positions",
            return_value=[],
        )
        result = await get_positions()

        assert result["result"]["positions"] == []
        assert result["result"]["message"] == "No open stock positions found."
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_positions_zero_quantity(self, mocker):
        """Test positions filtering out zero quantities."""
        mock_positions = [
            {
                "instrument": "test-instrument-url",
                "quantity": "0.00000000",  # Zero quantity should be filtered out
                "average_buy_price": "100.00",
                "updated_at": "2023-01-01T00:00:00Z",
            }
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.get_open_stock_positions",
            return_value=mock_positions,
        )
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.get_symbol_by_url",
            return_value="AAPL",
        )
        result = await get_positions()

        assert result["result"]["count"] == 0
        assert result["result"]["positions"] == []
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_positions_exception(self, mocker):
        """Test positions retrieval with exception."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.get_open_stock_positions",
            side_effect=Exception("Positions Error"),
        )
        result = await get_positions()

        assert "Positions Error" in result["result"]["error"]
        assert result["result"]["status"] == "error"


class TestPortfolioHistory:
    """Test portfolio_history tool."""

    @pytest.mark.asyncio
    async def test_get_portfolio_history_success_list_format(self, mocker):
        """Test successful portfolio history retrieval with list format."""
        mock_history = [
            {"begins_at": "2023-01-01T00:00:00Z", "adjusted_close_equity": "1000.00"},
            {"begins_at": "2023-01-02T00:00:00Z", "adjusted_close_equity": "1050.00"},
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.get_historical_portfolio",
            return_value=mock_history,
        )
        result = await get_portfolio_history("week")

        assert result["result"]["span"] == "week"
        assert result["result"]["total_return"] == "N/A"
        assert result["result"]["data_points_count"] == 2
        assert len(result["result"]["recent_performance"]) == 2
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_portfolio_history_success_dict_format(self, mocker):
        """Test successful portfolio history retrieval with dict format."""
        mock_history = {
            "historicals": [
                {
                    "begins_at": "2023-01-01T00:00:00Z",
                    "adjusted_close_equity": "1000.00",
                }
            ],
            "total_return": "50.00",
        }

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.get_historical_portfolio",
            return_value=mock_history,
        )
        result = await get_portfolio_history("month")

        assert result["result"]["span"] == "month"
        assert result["result"]["total_return"] == "50.00"
        assert result["result"]["data_points_count"] == 1
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_portfolio_history_with_none_values(self, mocker):
        """Test portfolio history handles None values in data."""
        mock_history = [
            {"begins_at": "2023-01-01T00:00:00Z", "adjusted_close_equity": "1000.00"},
            None,  # None value should be filtered out
            {"begins_at": "2023-01-02T00:00:00Z", "adjusted_close_equity": "1050.00"},
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.get_historical_portfolio",
            return_value=mock_history,
        )
        result = await get_portfolio_history()

        assert result["result"]["data_points_count"] == 3
        assert len(result["result"]["recent_performance"]) == 2  # None filtered out
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_portfolio_history_no_data(self, mocker):
        """Test portfolio history retrieval with no data."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.get_historical_portfolio",
            return_value=None,
        )
        result = await get_portfolio_history()

        assert result["result"]["message"] == "No portfolio history found."
        assert result["result"]["status"] == "no_data"

    @pytest.mark.asyncio
    async def test_get_portfolio_history_exception(self, mocker):
        """Test portfolio history retrieval with exception."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.get_historical_portfolio",
            side_effect=Exception("History Error"),
        )
        result = await get_portfolio_history()

        assert "History Error" in result["result"]["error"]
        assert result["result"]["status"] == "error"
