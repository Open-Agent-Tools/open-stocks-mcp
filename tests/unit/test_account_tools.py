"""Unit tests for account tools."""

from unittest.mock import patch

import pytest

from open_stocks_mcp.tools.robinhood_account_tools import (
    get_account_details,
    get_account_info,
    get_portfolio,
    get_positions,
)


class TestAccountTools:
    """Test account tools with mocked responses."""

    @patch("open_stocks_mcp.tools.robinhood_account_tools.rh.load_user_profile")
    @pytest.mark.asyncio
    async def test_get_account_info_success(self, mock_profile):
        """Test successful account info retrieval."""
        mock_profile.return_value = {
            "username": "testuser",
            "created_at": "2023-01-01T00:00:00Z",
        }

        result = await get_account_info()

        assert "result" in result
        assert result["result"]["username"] == "testuser"
        assert result["result"]["created_at"] == "2023-01-01T00:00:00Z"

    @patch("open_stocks_mcp.tools.robinhood_account_tools.rh.load_user_profile")
    @pytest.mark.asyncio
    async def test_get_account_info_error(self, mock_profile):
        """Test account info error handling."""
        mock_profile.side_effect = Exception("API Error")

        result = await get_account_info()

        assert "result" in result
        assert "error" in result["result"]

    @patch("open_stocks_mcp.tools.robinhood_account_tools.rh.load_portfolio_profile")
    @pytest.mark.asyncio
    async def test_get_portfolio_success(self, mock_portfolio):
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
    async def test_get_positions_success(self, mock_positions, mock_symbol):
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
    async def test_get_account_details_success(self, mock_account):
        """Test successful account details retrieval."""
        mock_account.return_value = {
            "account_number": "123456789",
            "buying_power": "1000.00",
        }

        result = await get_account_details()

        assert "result" in result
        assert isinstance(result["result"], dict)
