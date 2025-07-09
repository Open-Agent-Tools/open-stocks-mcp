"""
Tests for Advanced Portfolio Analytics Tools.

This module tests the advanced portfolio analytics functions including:
- build_holdings() with dividend information
- build_user_profile() with financial totals
- get_day_trades() for pattern day trading tracking
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from open_stocks_mcp.tools.robinhood_advanced_portfolio_tools import (
    get_build_holdings,
    get_build_user_profile,
    get_day_trades,
)


class TestAdvancedPortfolioTools:
    """Test suite for advanced portfolio analytics tools."""

    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager for testing."""
        mock_session = Mock()
        mock_session.is_authenticated.return_value = True
        mock_session.is_session_valid.return_value = True
        return mock_session

    @pytest.fixture
    def mock_rate_limiter(self):
        """Mock rate limiter for testing."""
        mock_limiter = Mock()
        mock_limiter.acquire = AsyncMock()
        return mock_limiter

    @pytest.fixture
    def sample_holdings_data(self):
        """Sample holdings data for testing."""
        return {
            "AAPL": {
                "price": "150.00",
                "quantity": "10",
                "average_buy_price": "145.00",
                "equity": "1500.00",
                "percent_change": "3.45",
                "equity_change": "50.00",
                "type": "stock",
                "name": "Apple Inc",
                "id": "450dfc6d-5510-4d40-abfb-f633b7d9be3e",
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
                "id": "943c5009-a0bb-4665-8cf4-a95dab5874e4",
                "pe_ratio": "22.1",
                "percentage": "84.8",
            },
        }

    @pytest.fixture
    def sample_user_profile_data(self):
        """Sample user profile data for testing."""
        return {
            "equity": "50000.00",
            "extended_hours_equity": "50100.00",
            "cash": "2500.00",
            "dividend_total": "1245.67",
            "total_return_today": "250.00",
            "total_return_today_percent": "0.50",
        }

    @pytest.fixture
    def sample_account_profile_data(self):
        """Sample account profile data for testing."""
        return {
            "day_trade_count": "2",
            "is_pattern_day_trader": False,
            "day_trade_buying_power": "25000.00",
            "overnight_buying_power": "12500.00",
            "max_ach_early_access_amount": "1000.00",
        }

    @pytest.mark.asyncio
    async def test_get_build_holdings_success(
        self, mock_session_manager, mock_rate_limiter, sample_holdings_data
    ):
        """Test successful build_holdings retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_holdings_data

            result = await get_build_holdings()

            assert result["result"]["status"] == "success"
            assert result["result"]["total_positions"] == 2
            assert "holdings" in result["result"]
            assert "AAPL" in result["result"]["holdings"]
            assert "GOOGL" in result["result"]["holdings"]
            assert result["result"]["holdings"]["AAPL"]["price"] == "150.00"
            assert result["result"]["holdings"]["GOOGL"]["equity"] == "14000.00"

    @pytest.mark.asyncio
    async def test_get_build_holdings_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test build_holdings when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_build_holdings()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["message"] == "No holdings found"
            assert result["result"]["holdings"] == {}

    @pytest.mark.asyncio
    async def test_get_build_holdings_empty_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test build_holdings with empty holdings data."""
        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = {}

            result = await get_build_holdings()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["total_positions"] == 0
            assert result["result"]["holdings"] == {}

    @pytest.mark.asyncio
    async def test_get_build_user_profile_success(
        self, mock_session_manager, mock_rate_limiter, sample_user_profile_data
    ):
        """Test successful build_user_profile retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_user_profile_data

            result = await get_build_user_profile()

            assert result["result"]["status"] == "success"
            assert result["result"]["equity"] == "50000.00"
            assert result["result"]["cash"] == "2500.00"
            assert result["result"]["dividend_total"] == "1245.67"
            assert result["result"]["total_return_today"] == "250.00"
            assert result["result"]["total_return_today_percent"] == "0.50"

    @pytest.mark.asyncio
    async def test_get_build_user_profile_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test build_user_profile when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_build_user_profile()

            assert result["result"]["status"] == "no_data"
            assert "error" in result["result"]
            assert "No user profile data available" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_day_trades_success(
        self, mock_session_manager, mock_rate_limiter, sample_account_profile_data
    ):
        """Test successful day trades information retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_account_profile_data

            result = await get_day_trades()

            assert result["result"]["status"] == "success"
            assert result["result"]["day_trade_count"] == 2
            assert result["result"]["remaining_day_trades"] == 1
            assert result["result"]["pattern_day_trader"] is False
            assert result["result"]["day_trade_buying_power"] == "25000.00"
            assert result["result"]["overnight_buying_power"] == "12500.00"

    @pytest.mark.asyncio
    async def test_get_day_trades_pdt_status(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test day trades information for pattern day trader."""
        pdt_data = {
            "day_trade_count": "4",
            "is_pattern_day_trader": True,
            "day_trade_buying_power": "100000.00",
            "overnight_buying_power": "50000.00",
            "max_ach_early_access_amount": "5000.00",
        }

        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = pdt_data

            result = await get_day_trades()

            assert result["result"]["status"] == "success"
            assert result["result"]["day_trade_count"] == 4
            assert (
                result["result"]["remaining_day_trades"] == 0
            )  # Max is already exceeded
            assert result["result"]["pattern_day_trader"] is True
            assert result["result"]["day_trade_buying_power"] == "100000.00"

    @pytest.mark.asyncio
    async def test_get_day_trades_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test day trades information when no account data is available."""
        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_day_trades()

            assert result["result"]["status"] == "no_data"
            assert "error" in result["result"]
            assert "No account profile data available" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_day_trades_missing_fields(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test day trades information with missing fields in account data."""
        incomplete_data = {
            "day_trade_count": "1",
            # Missing other fields
        }

        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = incomplete_data

            result = await get_day_trades()

            assert result["result"]["status"] == "success"
            assert result["result"]["day_trade_count"] == 1
            assert result["result"]["remaining_day_trades"] == 2
            assert result["result"]["pattern_day_trader"] is False  # Default
            assert result["result"]["day_trade_buying_power"] == "0.00"  # Default
            assert result["result"]["overnight_buying_power"] == "0.00"  # Default

    @pytest.mark.asyncio
    async def test_build_holdings_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for build_holdings."""
        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_build_holdings()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_build_user_profile_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for build_user_profile."""
        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_build_user_profile()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_day_trades_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for day trades information."""
        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_day_trades()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]
            assert "Failed to get day trading information" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_day_trades_remaining_calculation(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test remaining day trades calculation logic."""
        test_cases = [
            ("0", 3),  # 0 trades = 3 remaining
            ("1", 2),  # 1 trade = 2 remaining
            ("2", 1),  # 2 trades = 1 remaining
            ("3", 0),  # 3 trades = 0 remaining
            ("4", 0),  # 4 trades = 0 remaining (PDT)
        ]

        for day_trade_count, expected_remaining in test_cases:
            account_data = {
                "day_trade_count": day_trade_count,
                "is_pattern_day_trader": int(day_trade_count) >= 4,
                "day_trade_buying_power": "25000.00",
                "overnight_buying_power": "12500.00",
            }

            with patch(
                "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
            ) as mock_execute:
                mock_execute.return_value = account_data

                result = await get_day_trades()

                assert result["result"]["status"] == "success"
                assert result["result"]["day_trade_count"] == int(day_trade_count)
                assert result["result"]["remaining_day_trades"] == expected_remaining

    @pytest.mark.asyncio
    async def test_holdings_data_structure(
        self, mock_session_manager, mock_rate_limiter, sample_holdings_data
    ):
        """Test that holdings data structure is preserved correctly."""
        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_holdings_data

            result = await get_build_holdings()

            # Check that all expected fields are present for each holding
            holdings = result["result"]["holdings"]
            for _symbol, data in holdings.items():
                assert "price" in data
                assert "quantity" in data
                assert "average_buy_price" in data
                assert "equity" in data
                assert "percent_change" in data
                assert "equity_change" in data
                assert "type" in data
                assert "name" in data
                assert "id" in data

    @pytest.mark.asyncio
    async def test_user_profile_data_structure(
        self, mock_session_manager, mock_rate_limiter, sample_user_profile_data
    ):
        """Test that user profile data structure is preserved correctly."""
        with patch(
            "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_user_profile_data

            result = await get_build_user_profile()

            # Check that all expected financial fields are present
            profile = result["result"]
            assert "equity" in profile
            assert "extended_hours_equity" in profile
            assert "cash" in profile
            assert "dividend_total" in profile
            assert "total_return_today" in profile
            assert "total_return_today_percent" in profile
            assert "status" in profile
