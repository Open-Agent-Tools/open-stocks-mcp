"""Tests for robinhood_stock_tools module."""

import pytest

from open_stocks_mcp.tools.robinhood_stock_tools import (
    get_market_hours,
    get_price_history,
    get_stock_info,
    get_stock_price,
    search_stocks,
)


class TestStockPrice:
    """Test stock_price tool."""

    @pytest.mark.asyncio
    async def test_get_stock_price_success(self, mocker):
        """Test successful stock price retrieval."""
        mock_price_data = ["150.25"]
        mock_quote_data = [
            {
                "previous_close": "148.50",
                "volume": "50000000",
                "ask_price": "150.30",
                "bid_price": "150.20",
                "last_trade_price": "150.25",
            }
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_latest_price",
            return_value=mock_price_data,
        )
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_quotes",
            return_value=mock_quote_data,
        )
        result = await get_stock_price("AAPL")

        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["price"] == 150.25
        assert result["result"]["change"] == 1.75
        assert result["result"]["change_percent"] == 1.18
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_stock_price_no_data(self, mocker):
        """Test stock price retrieval with no data."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_latest_price",
            return_value=None,
        )
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_quotes",
            return_value=None,
        )
        result = await get_stock_price("AAPL")  # Use valid symbol to pass validation

        assert result["result"]["message"] == "No price data found for symbol: AAPL"
        assert result["result"]["status"] == "no_data"

    @pytest.mark.asyncio
    async def test_get_stock_price_exception(self, mocker):
        """Test stock price retrieval with exception."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_latest_price",
            side_effect=Exception("API Error"),
        )
        result = await get_stock_price("AAPL")

        assert "API error: API Error" in result["result"]["error"]
        assert result["result"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_get_stock_price_invalid_symbol(self, mocker):
        """Test stock price retrieval with invalid symbol."""
        result = await get_stock_price("INVALID123")

        assert "Invalid symbol format" in result["result"]["error"]
        assert result["result"]["status"] == "error"


class TestStockInfo:
    """Test stock_info tool."""

    @pytest.mark.asyncio
    async def test_get_stock_info_success(self, mocker):
        """Test successful stock info retrieval."""
        mock_fundamentals = [
            {
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "description": "Apple Inc. designs and manufactures consumer electronics",
                "market_cap": "3000000000000",
                "pe_ratio": "28.5",
                "dividend_yield": "0.0050",
                "high_52_weeks": "200.00",
                "low_52_weeks": "120.00",
                "average_volume": "75000000",
            }
        ]
        mock_instruments = [{"simple_name": "Apple", "tradeable": True}]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_fundamentals",
            return_value=mock_fundamentals,
        )
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_instruments_by_symbols",
            return_value=mock_instruments,
        )
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_name_by_symbol",
            return_value="Apple Inc.",
        )
        result = await get_stock_info("AAPL")

        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["company_name"] == "Apple Inc."
        assert result["result"]["sector"] == "Technology"
        assert result["result"]["industry"] == "Consumer Electronics"
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_stock_info_no_data(self, mocker):
        """Test stock info retrieval with no data."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_fundamentals",
            return_value=None,
        )
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_instruments_by_symbols",
            return_value=None,
        )
        result = await get_stock_info("AAPL")  # Use valid symbol to pass validation

        assert (
            result["result"]["message"]
            == "No company information found for symbol: AAPL"
        )
        assert result["result"]["status"] == "no_data"

    @pytest.mark.asyncio
    async def test_get_stock_info_exception(self, mocker):
        """Test stock info retrieval with exception."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_fundamentals",
            side_effect=Exception("Fundamentals Error"),
        )
        result = await get_stock_info("AAPL")

        assert "Fundamentals Error" in result["result"]["error"]
        assert result["result"]["status"] == "error"


class TestSearchStocks:
    """Test search_stocks tool."""

    @pytest.mark.asyncio
    async def test_search_stocks_success(self, mocker):
        """Test successful stock search."""
        mock_search_results = [
            {
                "symbol": "AAPL",
                "simple_name": "Apple Inc.",
                "tradeable": True,
                "country": "US",
                "type": "stock",
            },
            {
                "symbol": "APLE",
                "simple_name": "Apple Hospitality",
                "tradeable": True,
                "country": "US",
                "type": "stock",
            },
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.find_instrument_data",
            return_value=mock_search_results,
        )
        result = await search_stocks("apple")

        assert result["result"]["query"] == "apple"
        assert result["result"]["count"] == 2
        assert result["result"]["results"][0]["symbol"] == "AAPL"
        assert result["result"]["results"][0]["name"] == "Apple Inc."
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_search_stocks_no_results(self, mocker):
        """Test stock search with no results."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.find_instrument_data",
            return_value=None,
        )
        result = await search_stocks("nonexistent")

        assert result["result"]["query"] == "nonexistent"
        assert result["result"]["count"] == 0
        assert result["result"]["results"] == []
        assert (
            result["result"]["message"] == "No stocks found matching query: nonexistent"
        )
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_search_stocks_exception(self, mocker):
        """Test stock search with exception."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.find_instrument_data",
            side_effect=Exception("Search Error"),
        )
        result = await search_stocks("apple")

        assert "Search Error" in result["result"]["error"]
        assert result["result"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_search_stocks_filters_invalid_symbols(self, mocker):
        """Test search filters out results without valid symbols."""
        mock_search_results = [
            {
                "symbol": "AAPL",
                "simple_name": "Apple Inc.",
                "tradeable": True,
                "country": "US",
                "type": "stock",
            },
            {
                "symbol": "",  # Invalid symbol - should be filtered out
                "simple_name": "Invalid Company",
                "tradeable": False,
                "country": "US",
                "type": "stock",
            },
            {
                "simple_name": "No Symbol Company",  # Missing symbol - should be filtered out
                "tradeable": True,
                "country": "US",
                "type": "stock",
            },
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.find_instrument_data",
            return_value=mock_search_results,
        )
        result = await search_stocks("test")

        assert result["result"]["count"] == 1
        assert result["result"]["results"][0]["symbol"] == "AAPL"
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_search_stocks_empty_query(self, mocker):
        """Test search with empty query."""
        result = await search_stocks("")

        assert "Search query cannot be empty" in result["result"]["error"]
        assert result["result"]["status"] == "error"


class TestMarketHours:
    """Test market_hours tool."""

    @pytest.mark.asyncio
    async def test_get_market_hours_success(self, mocker):
        """Test successful market hours retrieval."""
        mock_markets = [
            {
                "name": "NASDAQ",
                "mic": "XNAS",
                "operating_mic": "XNAS",
                "timezone": "US/Eastern",
                "website": "https://www.nasdaq.com",
            },
            {
                "name": "NYSE",
                "mic": "XNYS",
                "operating_mic": "XNYS",
                "timezone": "US/Eastern",
                "website": "https://www.nyse.com",
            },
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_markets",
            return_value=mock_markets,
        )
        result = await get_market_hours()

        assert result["result"]["count"] == 2
        assert result["result"]["markets"][0]["name"] == "NASDAQ"
        assert result["result"]["markets"][0]["mic"] == "XNAS"
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_market_hours_no_data(self, mocker):
        """Test market hours retrieval with no data."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_markets",
            return_value=None,
        )
        result = await get_market_hours()

        assert result["result"]["message"] == "No market data available"
        assert result["result"]["status"] == "no_data"

    @pytest.mark.asyncio
    async def test_get_market_hours_exception(self, mocker):
        """Test market hours retrieval with exception."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_markets",
            side_effect=Exception("Market Hours Error"),
        )
        result = await get_market_hours()

        assert "Market Hours Error" in result["result"]["error"]
        assert result["result"]["status"] == "error"


class TestPriceHistory:
    """Test price_history tool."""

    @pytest.mark.asyncio
    async def test_get_price_history_success(self, mocker):
        """Test successful price history retrieval."""
        mock_historical_data = [
            {
                "begins_at": "2023-01-01T00:00:00Z",
                "open_price": "150.00",
                "high_price": "155.00",
                "low_price": "149.00",
                "close_price": "153.00",
                "volume": "1000000",
            },
            {
                "begins_at": "2023-01-02T00:00:00Z",
                "open_price": "153.00",
                "high_price": "158.00",
                "low_price": "152.00",
                "close_price": "157.00",
                "volume": "1200000",
            },
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_stock_historicals",
            return_value=mock_historical_data,
        )
        result = await get_price_history("AAPL", "week")

        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["period"] == "week"
        assert result["result"]["interval"] == "hour"
        assert result["result"]["count"] == 2
        assert result["result"]["data_points"][0]["open"] == 150.0
        assert result["result"]["data_points"][0]["close"] == 153.0
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_price_history_no_data(self, mocker):
        """Test price history retrieval with no data."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_stock_historicals",
            return_value=None,
        )
        result = await get_price_history(
            "AAPL", "week"
        )  # Use valid symbol to pass validation

        assert (
            result["result"]["message"] == "No historical data found for AAPL over week"
        )
        assert result["result"]["status"] == "no_data"

    @pytest.mark.asyncio
    async def test_get_price_history_exception(self, mocker):
        """Test price history retrieval with exception."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_stock_historicals",
            side_effect=Exception("Historical Data Error"),
        )
        result = await get_price_history("AAPL", "week")

        assert "Historical Data Error" in result["result"]["error"]
        assert result["result"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_get_price_history_period_mapping(self, mocker):
        """Test price history period to interval mapping."""
        mock_historical_data = [
            {
                "begins_at": "2023-01-01T00:00:00Z",
                "open_price": "150.00",
                "high_price": "155.00",
                "low_price": "149.00",
                "close_price": "153.00",
                "volume": "1000000",
            }
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_stock_historicals",
            return_value=mock_historical_data,
        )

        # Test different period mappings
        periods_intervals = [
            ("day", "5minute"),
            ("week", "hour"),
            ("month", "day"),
            ("3month", "day"),
            ("year", "week"),
            ("5year", "week"),
        ]

        for period, expected_interval in periods_intervals:
            result = await get_price_history("AAPL", period)
            assert result["result"]["period"] == period
            assert result["result"]["interval"] == expected_interval
            assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_price_history_filters_none_values(self, mocker):
        """Test price history filters out None values and invalid data points."""
        mock_historical_data = [
            {
                "begins_at": "2023-01-01T00:00:00Z",
                "open_price": "150.00",
                "high_price": "155.00",
                "low_price": "149.00",
                "close_price": "153.00",
                "volume": "1000000",
            },
            None,  # Should be filtered out
            {
                "begins_at": "2023-01-02T00:00:00Z",
                "open_price": "153.00",
                "high_price": "158.00",
                "low_price": "152.00",
                "close_price": None,  # Missing close_price - should be filtered out
                "volume": "1200000",
            },
            {
                "begins_at": "2023-01-03T00:00:00Z",
                "open_price": "157.00",
                "high_price": "160.00",
                "low_price": "156.00",
                "close_price": "159.00",
                "volume": "900000",
            },
        ]

        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_stock_historicals",
            return_value=mock_historical_data,
        )
        result = await get_price_history("AAPL", "week")

        assert result["result"]["count"] == 2  # Only 2 valid data points
        assert result["result"]["data_points"][0]["close"] == 153.0
        assert result["result"]["data_points"][1]["close"] == 159.0
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_price_history_invalid_period(self, mocker):
        """Test price history with invalid period."""
        result = await get_price_history("AAPL", "invalid_period")

        assert "Invalid period" in result["result"]["error"]
        assert result["result"]["status"] == "error"
