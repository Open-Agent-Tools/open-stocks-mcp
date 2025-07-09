"""
Tests for Watchlist Management Tools.

This module tests the watchlist management functions including:
- Getting all watchlists
- Getting watchlist by name
- Adding symbols to watchlists
- Removing symbols from watchlists
- Watchlist performance analysis
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from open_stocks_mcp.tools.robinhood_watchlist_tools import (
    add_symbols_to_watchlist,
    get_all_watchlists,
    get_watchlist_by_name,
    get_watchlist_performance,
    remove_symbols_from_watchlist,
)


class TestWatchlistTools:
    """Test suite for watchlist management tools."""

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
    def sample_watchlists(self):
        """Sample watchlists data for testing."""
        return [
            {
                "name": "Tech Stocks",
                "url": "watchlist_url_1",
                "user": "user_url",
                "symbols": ["AAPL", "GOOGL", "MSFT"],
            },
            {
                "name": "Energy Stocks",
                "url": "watchlist_url_2",
                "user": "user_url",
                "symbols": ["XOM", "CVX"],
            },
        ]

    @pytest.fixture
    def sample_watchlist_content(self):
        """Sample watchlist content for testing."""
        return {
            "name": "Tech Stocks",
            "url": "watchlist_url_1",
            "user": "user_url",
            "symbols": ["AAPL", "GOOGL", "MSFT"],
        }

    @pytest.mark.asyncio
    async def test_get_all_watchlists_success(
        self, mock_session_manager, mock_rate_limiter, sample_watchlists
    ):
        """Test successful retrieval of all watchlists."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_watchlists

            result = await get_all_watchlists()

            assert result["result"]["status"] == "success"
            assert result["result"]["total_watchlists"] == 2
            assert len(result["result"]["watchlists"]) == 2
            assert result["result"]["watchlists"][0]["name"] == "Tech Stocks"
            assert result["result"]["watchlists"][0]["symbol_count"] == 3

    @pytest.mark.asyncio
    async def test_get_all_watchlists_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test get all watchlists when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_all_watchlists()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["total_watchlists"] == 0
            assert result["result"]["watchlists"] == []

    @pytest.mark.asyncio
    async def test_get_watchlist_by_name_success(
        self, mock_session_manager, mock_rate_limiter, sample_watchlist_content
    ):
        """Test successful retrieval of watchlist by name."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_watchlist_content

            result = await get_watchlist_by_name("Tech Stocks")

            assert result["result"]["status"] == "success"
            assert result["result"]["name"] == "Tech Stocks"
            assert result["result"]["symbol_count"] == 3
            assert result["result"]["symbols"] == ["AAPL", "GOOGL", "MSFT"]

    @pytest.mark.asyncio
    async def test_get_watchlist_by_name_not_found(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test get watchlist by name when not found."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_watchlist_by_name("Nonexistent Watchlist")

            assert result["result"]["status"] == "not_found"
            assert result["result"]["name"] == "Nonexistent Watchlist"
            assert result["result"]["symbol_count"] == 0

    @pytest.mark.asyncio
    async def test_get_watchlist_by_name_no_name(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test get watchlist by name with no name provided."""
        result = await get_watchlist_by_name("")

        assert result["result"]["status"] == "error"
        assert "Watchlist name is required" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_add_symbols_to_watchlist_success(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test successful addition of symbols to watchlist."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = {"success": True}

            result = await add_symbols_to_watchlist("Tech Stocks", ["AAPL", "GOOGL"])

            assert result["result"]["status"] == "success"
            assert result["result"]["watchlist_name"] == "Tech Stocks"
            assert result["result"]["symbols_added"] == ["AAPL", "GOOGL"]
            assert result["result"]["symbols_count"] == 2
            assert result["result"]["success"] is True

    @pytest.mark.asyncio
    async def test_add_symbols_to_watchlist_no_name(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test add symbols to watchlist with no name provided."""
        result = await add_symbols_to_watchlist("", ["AAPL"])

        assert result["result"]["status"] == "error"
        assert "Watchlist name is required" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_add_symbols_to_watchlist_no_symbols(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test add symbols to watchlist with no symbols provided."""
        result = await add_symbols_to_watchlist("Tech Stocks", [])

        assert result["result"]["status"] == "error"
        assert "At least one symbol is required" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_add_symbols_to_watchlist_invalid_symbols(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test add symbols to watchlist with invalid symbols."""
        result = await add_symbols_to_watchlist("Tech Stocks", ["", "  ", None])

        assert result["result"]["status"] == "error"
        assert "No valid symbols provided" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_add_symbols_to_watchlist_api_failure(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test add symbols to watchlist when API call fails."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await add_symbols_to_watchlist("Tech Stocks", ["AAPL"])

            assert result["result"]["status"] == "error"
            assert result["result"]["success"] is False
            assert "Failed to add symbols to watchlist" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_remove_symbols_from_watchlist_success(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test successful removal of symbols from watchlist."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = {"success": True}

            result = await remove_symbols_from_watchlist(
                "Tech Stocks", ["AAPL", "GOOGL"]
            )

            assert result["result"]["status"] == "success"
            assert result["result"]["watchlist_name"] == "Tech Stocks"
            assert result["result"]["symbols_removed"] == ["AAPL", "GOOGL"]
            assert result["result"]["symbols_count"] == 2
            assert result["result"]["success"] is True

    @pytest.mark.asyncio
    async def test_remove_symbols_from_watchlist_no_name(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test remove symbols from watchlist with no name provided."""
        result = await remove_symbols_from_watchlist("", ["AAPL"])

        assert result["result"]["status"] == "error"
        assert "Watchlist name is required" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_remove_symbols_from_watchlist_no_symbols(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test remove symbols from watchlist with no symbols provided."""
        result = await remove_symbols_from_watchlist("Tech Stocks", [])

        assert result["result"]["status"] == "error"
        assert "At least one symbol is required" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_remove_symbols_from_watchlist_api_failure(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test remove symbols from watchlist when API call fails."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await remove_symbols_from_watchlist("Tech Stocks", ["AAPL"])

            assert result["result"]["status"] == "error"
            assert result["result"]["success"] is False
            assert (
                "Failed to remove symbols from watchlist" in result["result"]["error"]
            )

    @pytest.mark.asyncio
    async def test_get_watchlist_performance_success(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test successful watchlist performance retrieval."""

        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.get_watchlist_by_name"
        ) as mock_get_watchlist:
            mock_get_watchlist.return_value = {
                "result": {"status": "success", "symbols": ["AAPL", "GOOGL"]}
            }

            with patch(
                "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
            ) as mock_execute:
                mock_execute.side_effect = [
                    ["150.00"],
                    [{"previous_close": "145.00", "volume": "50000000"}],
                    ["2800.00"],
                    [{"previous_close": "2750.00", "volume": "1000000"}],
                ]

                result = await get_watchlist_performance("Tech Stocks")

                assert result["result"]["status"] == "success"
                assert result["result"]["watchlist_name"] == "Tech Stocks"
                assert result["result"]["summary"]["total_symbols"] == 2
                assert result["result"]["summary"]["gainers"] == 2
                assert result["result"]["summary"]["losers"] == 0

    @pytest.mark.asyncio
    async def test_get_watchlist_performance_no_name(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test get watchlist performance with no name provided."""
        result = await get_watchlist_performance("")

        assert result["result"]["status"] == "error"
        assert "Watchlist name is required" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_watchlist_performance_watchlist_not_found(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test get watchlist performance when watchlist is not found."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.get_watchlist_by_name"
        ) as mock_get_watchlist:
            mock_get_watchlist.return_value = {"result": {"status": "not_found"}}

            result = await get_watchlist_performance("Nonexistent Watchlist")

            assert result["result"]["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_get_watchlist_performance_no_symbols(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test get watchlist performance when watchlist has no symbols."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.get_watchlist_by_name"
        ) as mock_get_watchlist:
            mock_get_watchlist.return_value = {
                "result": {"status": "success", "symbols": []}
            }

            result = await get_watchlist_performance("Empty Watchlist")

            assert result["result"]["status"] == "no_data"
            assert result["result"]["summary"]["total_symbols"] == 0

    @pytest.mark.asyncio
    async def test_watchlist_tools_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for watchlist tools."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_all_watchlists()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_add_symbols_exception_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test exception handling for add symbols."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("Network Error")

            result = await add_symbols_to_watchlist("Tech Stocks", ["AAPL"])

            assert result["result"]["status"] == "error"
            assert result["result"]["success"] is False
            assert "Network Error" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_remove_symbols_exception_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test exception handling for remove symbols."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("Network Error")

            result = await remove_symbols_from_watchlist("Tech Stocks", ["AAPL"])

            assert result["result"]["status"] == "error"
            assert result["result"]["success"] is False
            assert "Network Error" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_symbol_formatting(self, mock_session_manager, mock_rate_limiter):
        """Test symbol formatting and validation."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = {"success": True}

            result = await add_symbols_to_watchlist(
                "Tech Stocks", ["  aapl  ", "googl", "MSFT"]
            )

            assert result["result"]["status"] == "success"
            assert result["result"]["symbols_added"] == ["AAPL", "GOOGL", "MSFT"]

    @pytest.mark.asyncio
    async def test_watchlist_performance_with_price_errors(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test watchlist performance when some price data fails."""
        with patch(
            "open_stocks_mcp.tools.robinhood_watchlist_tools.get_watchlist_by_name"
        ) as mock_get_watchlist:
            mock_get_watchlist.return_value = {
                "result": {"status": "success", "symbols": ["AAPL", "INVALID"]}
            }

            with patch(
                "open_stocks_mcp.tools.robinhood_watchlist_tools.execute_with_retry"
            ) as mock_execute:
                # First call succeeds, second fails
                mock_execute.side_effect = [
                    ["150.00"],
                    [{"previous_close": "145.00", "volume": "50000000"}],
                    Exception("Invalid symbol"),
                ]

                result = await get_watchlist_performance("Tech Stocks")

                assert result["result"]["status"] == "success"
                assert result["result"]["watchlist_name"] == "Tech Stocks"
                assert len(result["result"]["symbols"]) == 2
                assert result["result"]["symbols"][1]["symbol"] == "INVALID"
                assert result["result"]["symbols"][1]["current_price"] == "N/A"
