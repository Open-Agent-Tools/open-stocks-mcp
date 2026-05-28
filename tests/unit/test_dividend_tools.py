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

    @staticmethod
    def _configure_authenticated_session(mock_get_session_manager: Any) -> None:
        session = mock_get_session_manager.return_value
        session.ensure_authenticated = AsyncMock(return_value=True)

    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.get_session_manager")
    @pytest.mark.journey_research
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_dividends_success(
        self,
        mock_get_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test successful dividends retrieval."""
        self._configure_authenticated_session(mock_get_session_manager)
        mock_execute_with_retry.side_effect = [
            [
                {
                    "amount": "10.00",
                    "payable_date": "2023-01-15",
                    "state": "paid",
                    "instrument": "instrument://aapl",
                },
                {
                    "amount": "5.00",
                    "payable_date": "2023-02-15",
                    "state": "paid",
                    "instrument": "instrument://msft",
                },
            ],
            {"symbol": "AAPL", "simple_name": "Apple"},
            {"symbol": "MSFT", "simple_name": "Microsoft"},
        ]

        result = await get_dividends()

        assert "result" in result
        assert isinstance(result["result"], dict)
        calls = mock_execute_with_retry.call_args_list
        assert calls[0].args[0].__name__ == "get_dividends"
        assert calls[1].args[0].__name__ == "get_instrument_by_url"
        assert calls[2].args[0].__name__ == "get_instrument_by_url"

    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.get_session_manager")
    @pytest.mark.journey_research
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_total_dividends_success(
        self,
        mock_get_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test successful total dividends calculation."""
        self._configure_authenticated_session(mock_get_session_manager)
        mock_execute_with_retry.side_effect = [
            "100.50",
            [{"state": "paid", "paid_at": "2024-01-15T00:00:00Z", "amount": "10.00"}],
        ]

        result = await get_total_dividends()

        assert "result" in result
        assert isinstance(result["result"], dict)
        calls = mock_execute_with_retry.call_args_list
        assert calls[0].args[0].__name__ == "get_total_dividends"
        assert calls[1].args[0].__name__ == "get_dividends"

    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.get_session_manager")
    @pytest.mark.journey_research
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_dividends_by_instrument_success(
        self,
        mock_get_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test successful dividends by instrument retrieval."""
        self._configure_authenticated_session(mock_get_session_manager)
        mock_execute_with_retry.return_value = [
            {"amount": "10.00", "symbol": "AAPL"},
        ]

        result = await get_dividends_by_instrument("AAPL")

        assert "result" in result
        assert isinstance(result["result"], dict)
        call = mock_execute_with_retry.call_args
        assert call.args[0].__name__ == "get_dividends_by_instrument"
        assert call.args[1] == "AAPL"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.execute_with_retry")
    @pytest.mark.journey_research
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_dividends_error(self, mock_execute_with_retry: Any) -> None:
        """Test error handling."""
        mock_execute_with_retry.side_effect = Exception("API Error")

        result = await get_dividends()

        assert "result" in result
        assert "error" in result["result"]
