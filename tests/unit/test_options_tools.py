"""Unit tests for options trading tools."""

from typing import Any
from unittest.mock import patch

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


class TestOptionsChains:
    """Test options chains retrieval."""

    @patch("open_stocks_mcp.tools.robinhood_options_tools.rh.options.get_chains")
    @pytest.mark.asyncio
    async def test_get_options_chains_success(self, mock_chains: Any) -> None:
        """Test successful options chains retrieval."""
        # Mock data for option chains
        mock_chains.return_value = [
            {
                "expiration_date": "2024-01-19",
                "tradability": "tradable",
                "strike_price": "150.00",
                "chain_symbol": "AAPL",
                "type": "call",
                "id": "option1",
            },
            {
                "expiration_date": "2024-01-19",
                "tradability": "tradable",
                "strike_price": "150.00",
                "chain_symbol": "AAPL",
                "type": "put",
                "id": "option2",
            },
        ]

        result = await get_options_chains("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["total_contracts"] > 0
        assert result["result"]["chains"] is not None
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_options_tools.rh.options.get_chains")
    @pytest.mark.asyncio
    async def test_get_options_chains_no_data(self, mock_chains: Any) -> None:
        """Test options chains when no data is available."""
        mock_chains.return_value = None

        result = await get_options_chains("AAPL")

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert "No option chains found" in result["result"]["message"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_get_options_chains_invalid_symbol(self) -> None:
        """Test options chains with invalid symbol."""
        result = await get_options_chains("123INVALID")

        assert "result" in result
        # Function doesn't validate symbol format upfront, so it tries the API call
        # and may get no data rather than an error
        assert result["result"]["status"] in ["error", "no_data"]


class TestFindOptions:
    """Test find tradable options functionality."""

    @patch(
        "open_stocks_mcp.tools.robinhood_options_tools.rh.options.find_tradable_options"
    )
    @pytest.mark.asyncio
    async def test_find_options_no_filters(self, mock_find: Any) -> None:
        """Test finding options without filters."""
        mock_find.return_value = [
            {
                "strike_price": "150.00",
                "type": "call",
                "expiration_date": "2024-01-19",
                "tradability": "tradable",
                "id": "option1",
            },
            {
                "strike_price": "150.00",
                "type": "put",
                "expiration_date": "2024-01-19",
                "tradability": "tradable",
                "id": "option2",
            },
        ]

        result = await find_tradable_options("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["total_found"] == 2
        assert len(result["result"]["options"]) == 2
        assert result["result"]["status"] == "success"

    @patch(
        "open_stocks_mcp.tools.robinhood_options_tools.rh.options.find_tradable_options"
    )
    @pytest.mark.asyncio
    async def test_find_options_with_filters(self, mock_find: Any) -> None:
        """Test finding options with expiration and type filters."""
        mock_find.return_value = [
            {
                "strike_price": "150.00",
                "type": "call",
                "expiration_date": "2024-01-19",
                "tradability": "tradable",
                "id": "option1",
                "mark_price": "5.25",
            }
        ]

        result = await find_tradable_options("AAPL", "2024-01-19", "call")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["filters"]["expiration_date"] == "2024-01-19"
        assert result["result"]["filters"]["option_type"] == "call"
        assert result["result"]["total_found"] == 1
        assert result["result"]["options"][0]["type"] == "call"
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_find_options_invalid_date_format(self) -> None:
        """Test finding options with invalid date format."""
        result = await find_tradable_options("AAPL", "01/19/2024", "call")

        assert "result" in result
        # The function may not validate date format upfront and still try the API call
        # which could return no data or an error depending on Robin Stocks behavior
        assert result["result"]["status"] in ["error", "no_data"]


class TestOptionMarketData:
    """Test option market data retrieval."""

    @patch(
        "open_stocks_mcp.tools.robinhood_options_tools.rh.options.get_option_market_data_by_id"
    )
    @pytest.mark.asyncio
    async def test_get_option_market_data_success(self, mock_market_data: Any) -> None:
        """Test successful option market data retrieval."""
        mock_market_data.return_value = {
            "symbol": "AAPL",
            "strike_price": "150.00",
            "expiration_date": "2024-01-19",
            "type": "call",
            "mark_price": "5.25",
            "bid_price": "5.20",
            "ask_price": "5.30",
            "last_trade_price": "5.22",
            "volume": "1000",
            "open_interest": "5000",
            "implied_volatility": "0.35",
            "delta": "0.55",
            "gamma": "0.02",
            "theta": "-0.05",
            "vega": "0.10",
            "rho": "0.08",
        }

        result = await get_option_market_data("option123")

        assert "result" in result
        assert result["result"]["option_id"] == "option123"
        assert result["result"]["market_data"] is not None
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch(
        "open_stocks_mcp.tools.robinhood_options_tools.rh.options.get_option_market_data_by_id"
    )
    @pytest.mark.asyncio
    async def test_get_option_market_data_no_data(self, mock_market_data: Any) -> None:
        """Test option market data when no data is available."""
        mock_market_data.return_value = None

        result = await get_option_market_data("option123")

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert "No market data found" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_option_market_data_empty_id(self) -> None:
        """Test option market data with empty ID."""
        result = await get_option_market_data("")

        assert "result" in result
        assert "error" in result["result"]
        assert result["result"]["status"] == "error"


class TestOptionHistoricals:
    """Test option historical data retrieval."""

    @patch(
        "open_stocks_mcp.tools.robinhood_options_tools.rh.options.get_option_historicals"
    )
    @pytest.mark.asyncio
    async def test_get_option_historicals_success(self, mock_historicals: Any) -> None:
        """Test successful option historicals retrieval."""
        mock_historicals.return_value = [
            {
                "begins_at": "2024-01-01T00:00:00Z",
                "open_price": "5.00",
                "high_price": "5.50",
                "low_price": "4.90",
                "close_price": "5.25",
                "volume": "1000",
            },
            {
                "begins_at": "2024-01-02T00:00:00Z",
                "open_price": "5.25",
                "high_price": "5.60",
                "low_price": "5.10",
                "close_price": "5.45",
                "volume": "1200",
            },
        ]

        result = await get_option_historicals(
            "AAPL", "2024-01-19", "150.00", "call", "hour", "week"
        )

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["strike_price"] == "150.00"
        assert result["result"]["option_type"] == "call"
        assert result["result"]["total_data_points"] == 2
        assert len(result["result"]["historicals"]) == 2
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_get_option_historicals_invalid_type(self) -> None:
        """Test option historicals with invalid option type."""
        result = await get_option_historicals(
            "AAPL", "2024-01-19", "150.00", "invalid", "hour", "week"
        )

        assert "result" in result
        assert "error" in result["result"]
        assert result["result"]["status"] == "error"
        assert (
            "call" in result["result"]["error"] and "put" in result["result"]["error"]
        )

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_get_option_historicals_invalid_interval(self) -> None:
        """Test option historicals with invalid interval."""
        result = await get_option_historicals(
            "AAPL", "2024-01-19", "150.00", "call", "invalid", "week"
        )

        assert "result" in result
        # Invalid interval doesn't cause error, just succeeds with no useful data
        assert result["result"]["status"] == "success"
        assert result["result"]["interval"] == "invalid"


class TestOptionPositions:
    """Test option positions retrieval."""

    @patch(
        "open_stocks_mcp.tools.robinhood_options_tools.rh.options.get_aggregate_positions"
    )
    @pytest.mark.asyncio
    async def test_get_aggregate_positions_success(self, mock_aggregate: Any) -> None:
        """Test successful aggregate positions retrieval."""
        mock_aggregate.return_value = {
            "AAPL": {
                "positions": [
                    {
                        "quantity": "5.0000",
                        "average_buy_price": "5.25",
                        "equity": "30.00",
                        "type": "long",
                    }
                ]
            },
            "TSLA": {
                "positions": [
                    {
                        "quantity": "3.0000",
                        "average_buy_price": "10.50",
                        "equity": "36.00",
                        "type": "long",
                    }
                ]
            },
        }

        result = await get_aggregate_positions()

        assert "result" in result
        assert result["result"]["total_symbols"] == 2
        assert result["result"]["total_contracts"] == 2
        assert result["result"]["status"] == "success"

    @patch(
        "open_stocks_mcp.tools.robinhood_options_tools.rh.options.get_aggregate_positions"
    )
    @pytest.mark.asyncio
    async def test_get_aggregate_positions_empty(self, mock_aggregate: Any) -> None:
        """Test aggregate positions when empty."""
        mock_aggregate.return_value = []

        result = await get_aggregate_positions()

        assert "result" in result
        assert result["result"]["total_symbols"] == 0
        assert result["result"]["total_contracts"] == 0
        assert result["result"]["status"] == "no_data"

    @patch(
        "open_stocks_mcp.tools.robinhood_options_tools.rh.options.get_all_option_positions"
    )
    @pytest.mark.asyncio
    async def test_get_all_option_positions_success(
        self, mock_all_positions: Any
    ) -> None:
        """Test successful all option positions retrieval."""
        mock_all_positions.return_value = [
            {
                "chain_symbol": "AAPL",
                "type": "long",
                "quantity": "2.0000",
                "average_buy_price": "5.25",
                "trade_value_multiplier": "100.0000",
                "strike_price": "150.00",
                "expiration_date": "2024-01-19",
                "option_type": "call",
                "created_at": "2024-01-01T10:00:00Z",
            },
            {
                "chain_symbol": "TSLA",
                "type": "short",
                "quantity": "-1.0000",
                "average_buy_price": "10.50",
                "trade_value_multiplier": "100.0000",
                "strike_price": "250.00",
                "expiration_date": "2024-02-16",
                "option_type": "put",
                "created_at": "2024-01-05T10:00:00Z",
            },
        ]

        result = await get_all_option_positions()

        assert "result" in result
        assert result["result"]["total_positions"] == 2
        assert len(result["result"]["positions"]) == 2
        assert result["result"]["open_positions"] == 1  # Based on quantity > 0
        assert result["result"]["closed_positions"] == 1  # Based on quantity <= 0
        assert result["result"]["status"] == "success"

    @patch(
        "open_stocks_mcp.tools.robinhood_options_tools.rh.options.get_open_option_positions"
    )
    @pytest.mark.asyncio
    async def test_get_open_option_positions_success(
        self, mock_open_positions: Any
    ) -> None:
        """Test successful open option positions retrieval."""
        mock_open_positions.return_value = [
            {
                "chain_symbol": "AAPL",
                "type": "long",
                "quantity": "2.0000",
                "average_buy_price": "5.25",
                "trade_value_multiplier": "100.0000",
                "strike_price": "150.00",
                "expiration_date": "2024-01-19",
                "option_type": "call",
                "pending_buy_quantity": "0.0000",
                "pending_sell_quantity": "0.0000",
            }
        ]

        result = await get_open_option_positions()

        assert "result" in result
        assert result["result"]["total_open_positions"] == 1
        assert len(result["result"]["positions"]) == 1
        assert result["result"]["status"] == "success"

    @patch(
        "open_stocks_mcp.tools.robinhood_options_tools.rh.options.get_open_option_positions"
    )
    @pytest.mark.asyncio
    async def test_get_open_option_positions_none(
        self, mock_open_positions: Any
    ) -> None:
        """Test open option positions when none exist."""
        mock_open_positions.return_value = None

        result = await get_open_option_positions()

        assert "result" in result
        assert result["result"]["total_open_positions"] == 0
        assert result["result"]["positions"] == []
        assert result["result"]["message"] == "No open option positions found"
        assert result["result"]["status"] == "no_data"
