"""
Tests for Options Trading Tools.

This module tests the options trading analytics functions including:
- Options chains retrieval
- Tradable options search
- Option market data and Greeks
- Option position management
- Historical options data
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from open_stocks_mcp.tools.robinhood_options_tools import (
    find_tradable_options,
    get_aggregate_positions,
    get_all_option_positions,
    get_open_option_positions,
    get_option_historicals,
    get_option_market_data,
    get_options_chains,
)


class TestOptionsTools:
    """Test suite for options trading tools."""

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
    def sample_options_chains(self):
        """Sample options chains data for testing."""
        return [
            {
                "expiration_date": "2024-01-19",
                "strike_price": "150.00",
                "type": "call",
                "id": "call_option_id_1",
                "tradeable": True,
            },
            {
                "expiration_date": "2024-01-19",
                "strike_price": "150.00",
                "type": "put",
                "id": "put_option_id_1",
                "tradeable": True,
            },
            {
                "expiration_date": "2024-01-26",
                "strike_price": "155.00",
                "type": "call",
                "id": "call_option_id_2",
                "tradeable": True,
            },
        ]

    @pytest.fixture
    def sample_option_market_data(self):
        """Sample option market data for testing."""
        return {
            "option_id": "option_123",
            "symbol": "AAPL",
            "strike_price": "150.00",
            "expiration_date": "2024-01-19",
            "type": "call",
            "bid_price": "2.50",
            "ask_price": "2.55",
            "last_trade_price": "2.52",
            "volume": 1250,
            "open_interest": 5000,
            "implied_volatility": 0.25,
            "delta": 0.65,
            "gamma": 0.025,
            "theta": -0.12,
            "vega": 0.85,
            "rho": 0.15,
        }

    @pytest.fixture
    def sample_option_positions(self):
        """Sample option positions data for testing."""
        return [
            {
                "symbol": "AAPL",
                "strike_price": "150.00",
                "expiration_date": "2024-01-19",
                "type": "call",
                "quantity": "3",
                "average_price": "2.50",
                "current_price": "2.75",
                "total_equity": "825.00",
                "unrealized_pnl": "75.00",
                "status": "held",
            },
            {
                "symbol": "GOOGL",
                "strike_price": "2800.00",
                "expiration_date": "2024-02-16",
                "type": "put",
                "quantity": "1",
                "average_price": "45.00",
                "current_price": "42.00",
                "total_equity": "4200.00",
                "unrealized_pnl": "-300.00",
                "status": "held",
            },
        ]

    @pytest.mark.asyncio
    async def test_get_options_chains_success(
        self, mock_session_manager, mock_rate_limiter, sample_options_chains
    ):
        """Test successful options chains retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_options_chains

            result = await get_options_chains("AAPL")

            assert result["result"]["status"] == "success"
            assert result["result"]["symbol"] == "AAPL"
            assert result["result"]["total_contracts"] == 3
            assert len(result["result"]["chains"]) == 3
            assert result["result"]["chains"][0]["type"] == "call"
            assert result["result"]["chains"][1]["type"] == "put"

    @pytest.mark.asyncio
    async def test_get_options_chains_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test options chains when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_options_chains("AAPL")

            assert result["result"]["status"] == "no_data"
            assert result["result"]["symbol"] == "AAPL"
            assert result["result"]["total_contracts"] == 0
            assert result["result"]["chains"] == []

    @pytest.mark.asyncio
    async def test_get_options_chains_invalid_symbol(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test options chains with invalid symbol."""
        result = await get_options_chains("")

        assert result["result"]["status"] == "error"
        assert "Symbol is required" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_find_tradable_options_success(
        self, mock_session_manager, mock_rate_limiter, sample_options_chains
    ):
        """Test successful tradable options search."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_options_chains[:1]  # Only call options

            result = await find_tradable_options("AAPL", "2024-01-19", "call")

            assert result["result"]["status"] == "success"
            assert result["result"]["symbol"] == "AAPL"
            assert result["result"]["filters"]["expiration_date"] == "2024-01-19"
            assert result["result"]["filters"]["option_type"] == "call"
            assert result["result"]["total_found"] == 1

    @pytest.mark.asyncio
    async def test_find_tradable_options_invalid_type(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test tradable options search with invalid option type."""
        result = await find_tradable_options("AAPL", "2024-01-19", "invalid")

        assert result["result"]["status"] == "error"
        assert "Option type must be 'call' or 'put'" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_option_market_data_success(
        self, mock_session_manager, mock_rate_limiter, sample_option_market_data
    ):
        """Test successful option market data retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_option_market_data

            result = await get_option_market_data("option_123")

            assert result["result"]["status"] == "success"
            assert result["result"]["option_id"] == "option_123"
            assert result["result"]["market_data"]["symbol"] == "AAPL"
            assert result["result"]["market_data"]["delta"] == 0.65

    @pytest.mark.asyncio
    async def test_get_option_market_data_no_id(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test option market data with no ID provided."""
        result = await get_option_market_data("")

        assert result["result"]["status"] == "error"
        assert "Option ID is required" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_option_historicals_success(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test successful option historical data retrieval."""
        historical_data = [
            {
                "begins_at": "2024-01-15T09:30:00Z",
                "open_price": "2.50",
                "high_price": "2.65",
                "low_price": "2.45",
                "close_price": "2.60",
                "volume": 150,
            },
            {
                "begins_at": "2024-01-15T10:30:00Z",
                "open_price": "2.60",
                "high_price": "2.70",
                "low_price": "2.55",
                "close_price": "2.65",
                "volume": 120,
            },
        ]

        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = historical_data

            result = await get_option_historicals(
                "AAPL", "2024-01-19", "150.00", "call"
            )

            assert result["result"]["status"] == "success"
            assert result["result"]["symbol"] == "AAPL"
            assert result["result"]["strike_price"] == "150.00"
            assert result["result"]["option_type"] == "call"
            assert result["result"]["total_data_points"] == 2
            assert len(result["result"]["historicals"]) == 2

    @pytest.mark.asyncio
    async def test_get_option_historicals_invalid_type(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test option historicals with invalid option type."""
        result = await get_option_historicals("AAPL", "2024-01-19", "150.00", "invalid")

        assert result["result"]["status"] == "error"
        assert "Option type must be 'call' or 'put'" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_option_historicals_missing_params(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test option historicals with missing parameters."""
        result = await get_option_historicals("AAPL", "", "150.00", "call")

        assert result["result"]["status"] == "error"
        assert (
            "Expiration date and strike price are required" in result["result"]["error"]
        )

    @pytest.mark.asyncio
    async def test_get_aggregate_positions_success(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test successful aggregate positions retrieval."""
        aggregate_data = {
            "AAPL": {
                "total_contracts": 5,
                "net_quantity": 3,
                "average_price": "2.50",
                "total_equity": "750.00",
                "positions": [
                    {
                        "strike_price": "150.00",
                        "expiration_date": "2024-01-19",
                        "type": "call",
                        "quantity": "3",
                        "average_price": "2.50",
                    }
                ],
            }
        }

        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = aggregate_data

            result = await get_aggregate_positions()

            assert result["result"]["status"] == "success"
            assert result["result"]["total_symbols"] == 1
            assert result["result"]["total_contracts"] == 1
            assert "AAPL" in result["result"]["positions"]

    @pytest.mark.asyncio
    async def test_get_aggregate_positions_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test aggregate positions when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_aggregate_positions()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["total_symbols"] == 0
            assert result["result"]["total_contracts"] == 0
            assert result["result"]["positions"] == {}

    @pytest.mark.asyncio
    async def test_get_all_option_positions_success(
        self, mock_session_manager, mock_rate_limiter, sample_option_positions
    ):
        """Test successful all option positions retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_option_positions

            result = await get_all_option_positions()

            assert result["result"]["status"] == "success"
            assert result["result"]["total_positions"] == 2
            assert result["result"]["open_positions"] == 2
            assert result["result"]["closed_positions"] == 0

    @pytest.mark.asyncio
    async def test_get_all_option_positions_mixed_status(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test all option positions with mixed open/closed positions."""
        mixed_positions = [
            {"symbol": "AAPL", "quantity": "3", "status": "held"},
            {"symbol": "GOOGL", "quantity": "0", "status": "closed"},
        ]

        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = mixed_positions

            result = await get_all_option_positions()

            assert result["result"]["status"] == "success"
            assert result["result"]["total_positions"] == 2
            assert result["result"]["open_positions"] == 1
            assert result["result"]["closed_positions"] == 1

    @pytest.mark.asyncio
    async def test_get_open_option_positions_success(
        self, mock_session_manager, mock_rate_limiter, sample_option_positions
    ):
        """Test successful open option positions retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_option_positions

            result = await get_open_option_positions()

            assert result["result"]["status"] == "success"
            assert result["result"]["total_open_positions"] == 2
            assert float(result["result"]["total_equity"]) > 0
            assert float(result["result"]["total_unrealized_pnl"]) != 0

    @pytest.mark.asyncio
    async def test_get_open_option_positions_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test open option positions when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_open_option_positions()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["total_open_positions"] == 0
            assert result["result"]["total_equity"] == "0.00"
            assert result["result"]["total_unrealized_pnl"] == "0.00"

    @pytest.mark.asyncio
    async def test_options_chains_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for options chains."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_options_chains("AAPL")

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_find_tradable_options_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for tradable options search."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await find_tradable_options("AAPL", "2024-01-19", "call")

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_option_market_data_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for option market data."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_option_market_data("option_123")

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_option_historicals_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for option historicals."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_option_historicals(
                "AAPL", "2024-01-19", "150.00", "call"
            )

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_aggregate_positions_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for aggregate positions."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_aggregate_positions()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_all_option_positions_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for all option positions."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_all_option_positions()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_open_option_positions_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for open option positions."""
        with patch(
            "open_stocks_mcp.tools.robinhood_options_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_open_option_positions()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]
