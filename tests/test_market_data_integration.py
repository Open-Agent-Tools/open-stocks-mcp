"""Integration tests for market data tools."""

import os

import pytest
from dotenv import load_dotenv

from open_stocks_mcp.tools.robinhood_stock_tools import (
    get_market_hours,
    get_price_history,
    get_stock_info,
    get_stock_price,
    search_stocks,
)

# Load environment variables
load_dotenv()


def has_credentials():
    """Check if Robin Stocks credentials are available."""
    return bool(os.getenv("ROBINHOOD_USERNAME") and os.getenv("ROBINHOOD_PASSWORD"))


@pytest.mark.integration
@pytest.mark.skipif(not has_credentials(), reason="Robinhood credentials not available")
class TestMarketDataIntegration:
    """Integration tests for market data tools requiring live API access."""

    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Setup authentication for tests."""
        import robin_stocks.robinhood as rh

        # Login before tests
        username = os.getenv("ROBINHOOD_USERNAME")
        password = os.getenv("ROBINHOOD_PASSWORD")

        if username and password:
            rh.login(username, password, store_session=True)
            yield
            # Logout after tests
            rh.logout()
        else:
            yield

    @pytest.mark.asyncio
    @pytest.mark.live_market
    async def test_get_stock_price_integration(self):
        """Test getting stock price with live data."""
        # Test with a popular stock
        result = await get_stock_price("AAPL")

        assert result["result"]["status"] == "success"
        assert result["result"]["symbol"] == "AAPL"
        assert "price" in result["result"]
        assert result["result"]["price"] > 0
        assert "change" in result["result"]
        assert "change_percent" in result["result"]
        assert "volume" in result["result"]

        # Price should be reasonable for AAPL
        price = result["result"]["price"]
        assert 50 < price < 1000  # Reasonable range for AAPL

    @pytest.mark.asyncio
    async def test_get_stock_info_integration(self):
        """Test getting stock info with live data."""
        result = await get_stock_info("MSFT")

        assert result["result"]["status"] == "success"
        assert result["result"]["symbol"] == "MSFT"
        assert result["result"]["company_name"] == "Microsoft Corporation"
        assert result["result"]["sector"] == "Technology"
        assert "market_cap" in result["result"]
        assert "pe_ratio" in result["result"]
        assert result["result"]["tradeable"] is True

    @pytest.mark.asyncio
    async def test_search_stocks_integration(self):
        """Test searching stocks with live data."""
        result = await search_stocks("apple")

        assert result["result"]["status"] == "success"
        assert result["result"]["query"] == "apple"
        assert result["result"]["count"] > 0

        # Should find Apple Inc.
        symbols = [r["symbol"] for r in result["result"]["results"]]
        assert "AAPL" in symbols

        # Check first result structure
        first_result = result["result"]["results"][0]
        assert "symbol" in first_result
        assert "name" in first_result
        assert "tradeable" in first_result

    @pytest.mark.asyncio
    async def test_get_market_hours_integration(self):
        """Test getting market hours with live data."""
        result = await get_market_hours()

        assert result["result"]["status"] == "success"
        assert result["result"]["count"] > 0
        assert "markets" in result["result"]

        # Check for major markets
        market_names = [m["name"] for m in result["result"]["markets"]]
        assert any("NASDAQ" in name or "NYSE" in name for name in market_names)

        # Check market structure
        for market in result["result"]["markets"]:
            assert "name" in market
            assert "mic" in market
            assert "timezone" in market

    @pytest.mark.asyncio
    @pytest.mark.live_market
    async def test_get_price_history_integration(self):
        """Test getting price history with live data."""
        # Test different periods
        periods = ["day", "week", "month"]

        for period in periods:
            result = await get_price_history("GOOGL", period)

            assert result["result"]["status"] == "success"
            assert result["result"]["symbol"] == "GOOGL"
            assert result["result"]["period"] == period
            assert result["result"]["count"] > 0

            # Check data points
            data_points = result["result"]["data_points"]
            assert len(data_points) > 0

            # Check data point structure
            for point in data_points:
                assert "date" in point
                assert "open" in point
                assert "high" in point
                assert "low" in point
                assert "close" in point
                assert "volume" in point

                # Prices should be positive
                assert point["open"] > 0
                assert point["high"] >= point["low"]
                assert point["close"] > 0

    @pytest.mark.asyncio
    async def test_invalid_symbol_integration(self):
        """Test handling of invalid symbols."""
        result = await get_stock_price("INVALIDXYZ123")

        # Should return no_data or handle gracefully
        assert result["result"]["status"] in ["no_data", "error"]
        if result["result"]["status"] == "no_data":
            assert "message" in result["result"]

    @pytest.mark.asyncio
    async def test_search_stocks_empty_results_integration(self):
        """Test search with query that returns no results."""
        result = await search_stocks("xyzabc123notacompany")

        assert result["result"]["status"] == "success"
        assert result["result"]["count"] == 0
        assert result["result"]["results"] == []

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_multiple_stock_prices_integration(self):
        """Test getting prices for multiple stocks."""
        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "META"]

        for symbol in symbols:
            result = await get_stock_price(symbol)

            assert result["result"]["status"] == "success"
            assert result["result"]["symbol"] == symbol
            assert result["result"]["price"] > 0

    @pytest.mark.asyncio
    async def test_stock_info_for_etf_integration(self):
        """Test getting info for an ETF."""
        result = await get_stock_info("SPY")

        assert result["result"]["status"] == "success"
        assert result["result"]["symbol"] == "SPY"
        assert result["result"]["tradeable"] is True

    @pytest.mark.asyncio
    async def test_historical_data_consistency_integration(self):
        """Test that historical data is consistent."""
        result = await get_price_history("AAPL", "week")

        assert result["result"]["status"] == "success"

        # Check that data points are in chronological order
        data_points = result["result"]["data_points"]
        dates = [point["date"] for point in data_points]

        # Dates should be in ascending order
        for i in range(1, len(dates)):
            assert dates[i] >= dates[i - 1]


@pytest.mark.integration
class TestMarketDataMockIntegration:
    """Integration tests using mocks to test error scenarios."""

    @pytest.mark.asyncio
    async def test_network_error_handling(self, mocker):
        """Test handling of network errors."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_latest_price",
            side_effect=ConnectionError("Network is unreachable"),
        )

        result = await get_stock_price("AAPL")

        assert result["result"]["status"] == "error"
        assert "network" in result["result"]["error"].lower()

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, mocker):
        """Test handling of rate limit errors."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_quotes",
            side_effect=Exception("429 Too Many Requests"),
        )

        result = await get_stock_price("AAPL")

        assert result["result"]["status"] == "error"
        assert "rate limit" in result["result"]["error"].lower()

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, mocker):
        """Test handling of authentication errors."""
        mocker.patch(
            "open_stocks_mcp.tools.robinhood_stock_tools.rh.get_fundamentals",
            side_effect=Exception("401 Unauthorized"),
        )

        result = await get_stock_info("AAPL")

        assert result["result"]["status"] == "error"
        assert "authentication" in result["result"]["error"].lower()
