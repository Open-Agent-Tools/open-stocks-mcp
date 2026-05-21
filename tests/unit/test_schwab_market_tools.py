"""Unit tests for Schwab market data tools."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.schwab_market_tools import (
    get_schwab_instrument,
    get_schwab_price_history,
    get_schwab_quote,
    get_schwab_quotes,
    search_schwab_instruments,
)


class TestSchwabMarketTools:
    """Test Schwab market data tools with mocked responses."""

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    async def test_get_quote_success(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        mock_schwab_quote: Any,
    ) -> None:
        """Test successful stock quote retrieval."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.return_value = mock_schwab_quote

        result = await get_schwab_quote("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["last_price"] == 175.50
        assert result["result"]["bid_price"] == 175.45
        assert result["result"]["ask_price"] == 175.55

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    async def test_get_quote_auth_error(
        self, mock_get_broker: AsyncMock, mock_schwab_auth_error: Any
    ) -> None:
        """Test quote retrieval when authentication fails."""
        mock_get_broker.return_value = (None, mock_schwab_auth_error)

        result = await get_schwab_quote("AAPL")

        assert result == mock_schwab_auth_error

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    async def test_get_quotes_success(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        mock_schwab_quotes: Any,
    ) -> None:
        """Test successful multiple quotes retrieval."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.return_value = mock_schwab_quotes

        result = await get_schwab_quotes(["AAPL", "GOOGL"])

        assert "result" in result
        assert "quotes" in result["result"]
        assert len(result["result"]["quotes"]) == 2
        assert result["result"]["quotes"]["AAPL"]["last_price"] == 175.50
        assert result["result"]["quotes"]["GOOGL"]["last_price"] == 140.25

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_market_tools.Client")
    async def test_get_price_history_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: MagicMock,
        mock_get_broker: MagicMock,
        mock_schwab_price_history: Any,
    ) -> None:
        """Test successful price history retrieval."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.PriceHistory.PeriodType.DAY = "day"
        mock_client.PriceHistory.FrequencyType.MINUTE = "minute"
        mock_to_thread.return_value = mock_schwab_price_history

        result = await get_schwab_price_history("AAPL", "day", 1, "minute", 1)

        assert "result" in result
        assert "candles" in result["result"]
        assert len(result["result"]["candles"]) == 2
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["count"] == 2

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    async def test_get_price_history_invalid_period_type(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Test price history with invalid period type."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        result = await get_schwab_price_history(
            "AAPL", "invalid_period", 1, "minute", 1
        )

        assert "result" in result
        assert "error" in result["result"]
        assert "Invalid period_type" in result["result"]["error"]

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    async def test_get_instrument_success(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        mock_schwab_instrument: Any,
    ) -> None:
        """Test successful instrument retrieval."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.return_value = mock_schwab_instrument

        result = await get_schwab_instrument("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["description"] == "Apple Inc"
        assert result["result"]["exchange_name"] == "NASDAQ"

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    async def test_search_instruments_success(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        mock_schwab_instrument_search: Any,
    ) -> None:
        """Test successful instrument search."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.return_value = mock_schwab_instrument_search

        result = await search_schwab_instruments("AAPL")

        assert "result" in result
        assert "results" in result["result"]
        assert len(result["result"]["results"]) == 1
        assert result["result"]["results"][0]["symbol"] == "AAPL"

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.exception_test
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    async def test_get_quote_error(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test quote retrieval error handling."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.side_effect = Exception("API Error")

        result = await get_schwab_quote("AAPL")

        assert "result" in result
        assert "error" in result["result"]

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    @pytest.mark.parametrize(
        "function,args",
        [
            (get_schwab_quote, ("AAPL",)),
            (get_schwab_quotes, (["AAPL", "GOOGL"],)),
            (get_schwab_price_history, ("AAPL",)),
            (get_schwab_instrument, ("AAPL",)),
            (search_schwab_instruments, ("Apple",)),
        ],
    )
    async def test_market_api_failures_bulk(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        function,
        args,
    ) -> None:
        """Test various market tools for API failure responses."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.side_effect = Exception("API Error")

        result = await function(*args)
        assert result["result"]["status"] == "error"
        if function.__name__ != "search_schwab_instruments":
            assert "API Error" in result["result"]["error"]
