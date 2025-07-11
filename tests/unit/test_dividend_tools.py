"""Unit tests for dividend tools."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from open_stocks_mcp.tools.robinhood_dividend_tools import (
    get_dividends,
    get_dividends_by_instrument,
    get_total_dividends,
)


class TestDividendTools:
    """Test dividend tools with mocked responses."""

    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.asyncio.get_event_loop")
    @pytest.mark.asyncio
    async def test_get_dividends_success(self, mock_loop: Any) -> None:
        """Test successful dividends retrieval."""
        # Mock the event loop and run_in_executor
        mock_executor = AsyncMock()
        mock_executor.return_value = [
            {"amount": "10.00", "payable_date": "2023-01-15"},
            {"amount": "5.00", "payable_date": "2023-02-15"},
        ]

        mock_loop.return_value.run_in_executor = mock_executor

        result = await get_dividends()

        assert "result" in result
        assert isinstance(result["result"], dict)

    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.asyncio.get_event_loop")
    @pytest.mark.asyncio
    async def test_get_total_dividends_success(self, mock_loop: Any) -> None:
        """Test successful total dividends calculation."""
        # Mock the event loop and run_in_executor
        mock_executor = AsyncMock()
        mock_executor.return_value = "100.50"  # Total dividends as string

        mock_loop.return_value.run_in_executor = mock_executor

        result = await get_total_dividends()

        assert "result" in result
        assert isinstance(result["result"], dict)

    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.asyncio.get_event_loop")
    @pytest.mark.asyncio
    async def test_get_dividends_by_instrument_success(self, mock_loop: Any) -> None:
        """Test successful dividends by instrument retrieval."""
        # Mock the event loop and run_in_executor
        mock_executor = AsyncMock()
        mock_executor.return_value = [
            {"amount": "10.00", "symbol": "AAPL"},
        ]

        mock_loop.return_value.run_in_executor = mock_executor

        result = await get_dividends_by_instrument("AAPL")

        assert "result" in result
        assert isinstance(result["result"], dict)

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.asyncio.get_event_loop")
    @pytest.mark.asyncio
    async def test_get_dividends_error(self, mock_loop: Any) -> None:
        """Test error handling."""
        # Mock the event loop and run_in_executor to raise an exception
        mock_executor = AsyncMock()
        mock_executor.side_effect = Exception("API Error")

        mock_loop.return_value.run_in_executor = mock_executor

        result = await get_dividends()

        assert "result" in result
        assert "error" in result["result"]
