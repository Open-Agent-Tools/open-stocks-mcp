"""Unit tests for market data tools."""

from typing import Any
from unittest.mock import patch

import pytest

from open_stocks_mcp.tools.robinhood_market_data_tools import (
    get_stocks_by_tag,
    get_top_100,
    get_top_movers,
)


class TestMarketTools:
    """Test market data tools with mocked responses."""

    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.rh.get_top_movers")
    @pytest.mark.asyncio
    async def test_get_top_movers_success(self, mock_movers: Any) -> None:
        """Test successful top movers retrieval."""
        mock_movers.return_value = [
            {"symbol": "AAPL", "price": "150.00", "change": "5.00"},
            {"symbol": "GOOGL", "price": "2500.00", "change": "-10.00"},
        ]

        result = await get_top_movers()

        assert "result" in result
        assert isinstance(result["result"], dict)
        # The actual structure depends on how the tool processes the data

    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.rh.get_top_100")
    @pytest.mark.asyncio
    async def test_get_top_100_success(self, mock_top100: Any) -> None:
        """Test successful top 100 retrieval."""
        mock_top100.return_value = [
            {"symbol": "AAPL", "market_cap": "2000000000"},
            {"symbol": "MSFT", "market_cap": "1800000000"},
        ]

        result = await get_top_100()

        assert "result" in result
        assert isinstance(result["result"], dict)

    @patch(
        "open_stocks_mcp.tools.robinhood_market_data_tools.rh.get_all_stocks_from_market_tag"
    )
    @pytest.mark.asyncio
    async def test_get_stocks_by_tag_success(self, mock_stocks: Any) -> None:
        """Test successful stocks by tag retrieval."""
        mock_stocks.return_value = [
            {"symbol": "NVDA", "sector": "Technology"},
            {"symbol": "AMD", "sector": "Technology"},
        ]

        result = await get_stocks_by_tag("technology")

        assert "result" in result
        assert isinstance(result["result"], dict)

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.rh.get_top_movers")
    @pytest.mark.asyncio
    async def test_get_top_movers_error(self, mock_movers: Any) -> None:
        """Test error handling for top movers."""
        mock_movers.side_effect = Exception("API Error")

        result = await get_top_movers()

        assert "result" in result
        assert "error" in result["result"]
