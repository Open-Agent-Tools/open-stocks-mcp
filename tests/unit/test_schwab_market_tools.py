"""Unit tests for Schwab market data tools."""

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
    @patch("open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_market_tools.asyncio.to_thread")
    async def test_get_quote_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful stock quote retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock response
        mock_to_thread.return_value = {
            "AAPL": {
                "quote": {
                    "lastPrice": 175.50,
                    "bidPrice": 175.45,
                    "askPrice": 175.55,
                    "bidSize": 100,
                    "askSize": 200,
                    "totalVolume": 50000000,
                    "openPrice": 174.00,
                    "highPrice": 176.00,
                    "lowPrice": 173.50,
                    "closePrice": 174.50,
                    "netChange": 1.00,
                    "netPercentChange": 0.57,
                    "52WkHigh": 200.00,
                    "52WkLow": 125.00,
                }
            }
        }

        result = await get_schwab_quote("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["last_price"] == 175.50
        assert result["result"]["bid_price"] == 175.45
        assert result["result"]["ask_price"] == 175.55

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error")
    async def test_get_quote_auth_error(self, mock_get_broker: AsyncMock) -> None:
        """Test quote retrieval when authentication fails."""
        # Mock authentication error
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        result = await get_schwab_quote("AAPL")

        assert result == error_response

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_market_tools.asyncio.to_thread")
    async def test_get_quotes_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful multiple quotes retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock response
        mock_to_thread.return_value = {
            "AAPL": {
                "quote": {
                    "lastPrice": 175.50,
                    "netChange": 1.00,
                    "netPercentChange": 0.57,
                    "totalVolume": 50000000,
                    "bidPrice": 175.45,
                    "askPrice": 175.55,
                }
            },
            "GOOGL": {
                "quote": {
                    "lastPrice": 140.25,
                    "netChange": -2.50,
                    "netPercentChange": -1.75,
                    "totalVolume": 25000000,
                    "bidPrice": 140.20,
                    "askPrice": 140.30,
                }
            },
        }

        result = await get_schwab_quotes(["AAPL", "GOOGL"])

        assert "result" in result
        assert "quotes" in result["result"]
        assert len(result["result"]["quotes"]) == 2
        assert result["result"]["quotes"]["AAPL"]["last_price"] == 175.50
        assert result["result"]["quotes"]["GOOGL"]["last_price"] == 140.25

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_market_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_market_tools.Client")
    async def test_get_price_history_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful price history retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client enums
        mock_client.PriceHistory.PeriodType.DAY = "day"
        mock_client.PriceHistory.FrequencyType.MINUTE = "minute"

        # Mock response
        mock_to_thread.return_value = {
            "candles": [
                {
                    "open": 174.00,
                    "high": 175.00,
                    "low": 173.50,
                    "close": 174.50,
                    "volume": 1000000,
                    "datetime": 1672531200000,
                },
                {
                    "open": 174.50,
                    "high": 176.00,
                    "low": 174.00,
                    "close": 175.50,
                    "volume": 1500000,
                    "datetime": 1672534800000,
                },
            ],
            "empty": False,
        }

        result = await get_schwab_price_history("AAPL", "day", 1, "minute", 1)

        assert "result" in result
        assert "candles" in result["result"]
        assert len(result["result"]["candles"]) == 2
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["count"] == 2

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error")
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
    @patch("open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_market_tools.asyncio.to_thread")
    async def test_get_instrument_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful instrument retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock response
        mock_to_thread.return_value = {
            "AAPL": {
                "assetMainType": "EQUITY",
                "reference": {
                    "description": "Apple Inc",
                    "exchange": "Q",
                    "exchangeName": "NASDAQ",
                    "cusip": "037833100",
                },
            }
        }

        result = await get_schwab_instrument("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["description"] == "Apple Inc"
        assert result["result"]["exchange_name"] == "NASDAQ"

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_market_tools.asyncio.to_thread")
    async def test_search_instruments_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful instrument search."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock response
        mock_to_thread.return_value = {
            "AAPL": {
                "assetMainType": "EQUITY",
                "reference": {
                    "description": "Apple Inc",
                    "exchangeName": "NASDAQ",
                },
            }
        }

        result = await search_schwab_instruments("AAPL")

        assert "result" in result
        assert "results" in result["result"]
        assert len(result["result"]["results"]) == 1
        assert result["result"]["results"][0]["symbol"] == "AAPL"

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_market_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_market_tools.asyncio.to_thread")
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
