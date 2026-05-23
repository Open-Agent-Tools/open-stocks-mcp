"""Unit tests for Schwab market data tools."""

import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.schwab_market_tools import (
    get_schwab_instrument,
    get_schwab_instrument_by_cusip,
    get_schwab_market_hours,
    get_schwab_movers,
    get_schwab_movers_sp500,
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
        schwab_quote_payload: dict[str, Any],
    ) -> None:
        """Test successful stock quote retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_to_thread.return_value = schwab_quote_payload

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
        self,
        mock_get_broker: AsyncMock,
        broker_auth_error_payload: dict[str, Any],
    ) -> None:
        """Test quote retrieval when authentication fails."""
        mock_get_broker.return_value = (None, broker_auth_error_payload)

        result = await get_schwab_quote("AAPL")

        assert result == broker_auth_error_payload

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
        schwab_quotes_payload: dict[str, Any],
    ) -> None:
        """Test successful multiple quotes retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_to_thread.return_value = schwab_quotes_payload

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
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        schwab_price_history_payload: dict[str, Any],
    ) -> None:
        """Test successful price history retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client enums
        mock_client.PriceHistory.PeriodType.DAY = "day"
        mock_client.PriceHistory.FrequencyType.MINUTE = "minute"

        mock_to_thread.return_value = schwab_price_history_payload

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
        # Mock broker
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
        schwab_quote_payload: dict[str, Any],
    ) -> None:
        """Test successful instrument retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_to_thread.return_value = schwab_quote_payload

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
        schwab_quote_payload: dict[str, Any],
    ) -> None:
        """Test successful instrument search."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_to_thread.return_value = schwab_quote_payload

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
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock API error
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
        # Search has a custom error message, so we just check status
        if function.__name__ != "search_schwab_instruments":
            assert "API Error" in result["result"]["error"]


class TestSchwabMarketHours:
    """Tests for get_schwab_market_hours."""

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_market_tools.Client")
    async def test_get_market_hours_success(
        self,
        mock_client: MagicMock,
        mock_execute: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful market hours retrieval."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.MarketHours.Market.EQUITY = "equity"
        mock_execute.return_value = {"equity": {"isOpen": True, "sessionHours": {}}}

        result = await get_schwab_market_hours("equity", "2026-05-20")

        assert "result" in result
        assert result["result"]["market"] == "equity"
        assert "hours" in result["result"]

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_market_tools.Client")
    async def test_get_market_hours_passes_date_object(
        self,
        mock_client: MagicMock,
        mock_execute: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test that a date string is parsed into datetime.date before the call."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.MarketHours.Market.EQUITY = "equity"
        mock_execute.return_value = {}

        await get_schwab_market_hours("equity", "2026-05-20")

        # Grab the callable passed to execute_broker_request and call it
        call_args = mock_execute.call_args
        inner_fn = call_args[0][0]
        inner_fn()  # Triggers broker.client.get_market_hours(...)
        _, kwargs = mock_broker.client.get_market_hours.call_args
        assert kwargs["date"] == datetime.date(2026, 5, 20)

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    async def test_get_market_hours_invalid_market(
        self,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test market hours with invalid market string."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        result = await get_schwab_market_hours("invalid_market")

        assert "result" in result
        assert "error" in result["result"]

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    async def test_get_market_hours_auth_error(
        self,
        mock_get_broker: AsyncMock,
        broker_auth_error_payload: dict[str, Any],
    ) -> None:
        """Test market hours when auth fails."""
        mock_get_broker.return_value = (None, broker_auth_error_payload)

        result = await get_schwab_market_hours("equity")

        assert result == broker_auth_error_payload


class TestSchwabMovers:
    """Tests for get_schwab_movers and get_schwab_movers_sp500."""

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_market_tools.Client")
    async def test_get_movers_dji_success(
        self,
        mock_client: MagicMock,
        mock_execute: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test movers retrieval for $DJI."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Movers.Index.DJI = "$DJI"
        mock_execute.return_value = {"screeners": [{"symbol": "AAPL", "volume": 1000}]}

        result = await get_schwab_movers("$DJI")

        assert "result" in result
        assert result["result"]["index"] == "$DJI"
        assert "movers" in result["result"]

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_market_tools.Client")
    async def test_get_movers_nasdaq_success(
        self,
        mock_client: MagicMock,
        mock_execute: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test movers retrieval for NASDAQ."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Movers.Index.NASDAQ = "NASDAQ"
        mock_execute.return_value = {"screeners": []}

        result = await get_schwab_movers("NASDAQ")

        assert "result" in result
        assert result["result"]["index"] == "NASDAQ"

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    async def test_get_movers_invalid_index(
        self,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test movers with invalid index."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        result = await get_schwab_movers("INVALID_INDEX")

        assert "result" in result
        assert "error" in result["result"]
        assert "Invalid index" in result["result"]["error"]

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    async def test_get_movers_invalid_sort_order(
        self,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test movers with invalid sort order."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        result = await get_schwab_movers("$DJI", sort_order="INVALID_SORT")

        assert "result" in result
        assert "error" in result["result"]
        assert "Invalid sort_order" in result["result"]["error"]

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    async def test_get_movers_invalid_frequency(
        self,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test movers with invalid frequency."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        result = await get_schwab_movers("$DJI", frequency=999)

        assert "result" in result
        assert "error" in result["result"]
        assert "Invalid frequency" in result["result"]["error"]

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_market_tools.Client")
    async def test_get_movers_sp500_uses_spx(
        self,
        mock_client: MagicMock,
        mock_execute: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test that sp500 shortcut passes $SPX to the client."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Movers.Index.SPX = "$SPX"
        mock_execute.return_value = {"screeners": []}

        result = await get_schwab_movers_sp500()

        assert "result" in result
        assert result["result"]["index"] == "$SPX"

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    async def test_get_movers_auth_error(
        self,
        mock_get_broker: AsyncMock,
        broker_auth_error_payload: dict[str, Any],
    ) -> None:
        """Test movers when auth fails."""
        mock_get_broker.return_value = (None, broker_auth_error_payload)

        result = await get_schwab_movers("$DJI")

        assert result == broker_auth_error_payload


class TestSchwabInstrumentByCusip:
    """Tests for get_schwab_instrument_by_cusip."""

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    async def test_get_instrument_by_cusip_success(
        self,
        mock_execute: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful CUSIP instrument lookup preserving leading zeros."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_execute.return_value = {
            "cusip": "037833100",
            "symbol": "AAPL",
            "description": "Apple Inc",
            "exchange": "Q",
            "assetType": "EQUITY",
        }

        result = await get_schwab_instrument_by_cusip("037833100")

        assert "result" in result
        assert result["result"]["cusip"] == "037833100"
        assert result["result"]["symbol"] == "AAPL"

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_market_tools.execute_broker_request")
    async def test_get_instrument_by_cusip_passes_exact_string(
        self,
        mock_execute: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test CUSIP with whitespace is trimmed but leading zeros preserved."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_execute.return_value = {}

        await get_schwab_instrument_by_cusip("  037833100  ")

        call_args = mock_execute.call_args
        inner_fn = call_args[0][0]
        inner_fn()
        mock_broker.client.get_instrument_by_cusip.assert_called_once_with("037833100")

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    async def test_get_instrument_by_cusip_empty_string(
        self,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test CUSIP lookup with empty/blank CUSIP returns error."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        result = await get_schwab_instrument_by_cusip("   ")

        assert "result" in result
        assert "error" in result["result"]

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error"
    )
    async def test_get_instrument_by_cusip_auth_error(
        self,
        mock_get_broker: AsyncMock,
        broker_auth_error_payload: dict[str, Any],
    ) -> None:
        """Test CUSIP lookup when auth fails."""
        mock_get_broker.return_value = (None, broker_auth_error_payload)

        result = await get_schwab_instrument_by_cusip("037833100")

        assert result == broker_auth_error_payload
