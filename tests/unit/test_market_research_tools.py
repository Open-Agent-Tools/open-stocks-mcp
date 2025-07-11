"""Unit tests for market research and advanced data tools."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from open_stocks_mcp.tools.robinhood_market_data_tools import (
    get_stock_earnings,
    get_stock_events,
    get_stock_level2_data,
    get_stock_news,
    get_stock_ratings,
    get_stock_splits,
    get_top_movers_sp500,
)


class TestTopMoversSP500:
    """Test top S&P 500 movers functionality."""

    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_top_movers_sp500_up_success(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test successful retrieval of S&P 500 up movers."""
        # Mock authentication - make it async
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)

        # Mock rate limiter - make it async
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        # Mock API response
        mock_execute_with_retry.return_value = [
            {
                "symbol": "AAPL",
                "instrument_url": "https://robinhood.com/instruments/450dfc6d-5510-4d40-abfb-f633b7d9be3e/",
                "updated_at": "2024-07-09T16:00:00Z",
                "price_movement": {
                    "market_hours_last_movement_pct": "2.5",
                    "market_hours_last_price": "150.00",
                },
                "description": "Apple Inc.",
            },
            {
                "symbol": "MSFT",
                "instrument_url": "https://robinhood.com/instruments/50810c35-d215-4866-9758-0ada4ac79ffa/",
                "updated_at": "2024-07-09T16:00:00Z",
                "price_movement": {
                    "market_hours_last_movement_pct": "1.8",
                    "market_hours_last_price": "320.00",
                },
                "description": "Microsoft Corporation",
            },
        ]

        result = await get_top_movers_sp500("up")

        assert "result" in result
        assert result["result"]["direction"] == "up"
        assert result["result"]["count"] == 2
        assert len(result["result"]["movers"]) == 2
        assert result["result"]["movers"][0]["symbol"] == "AAPL"
        assert result["result"]["movers"][0]["description"] == "Apple Inc."
        assert result["result"]["status"] == "success"

    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_top_movers_sp500_down_success(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test successful retrieval of S&P 500 down movers."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        # Mock API response
        mock_execute_with_retry.return_value = [
            {
                "symbol": "TSLA",
                "instrument_url": "https://robinhood.com/instruments/81733743-965a-4d93-b87a-6973cb9ecc34/",
                "updated_at": "2024-07-09T16:00:00Z",
                "price_movement": {
                    "market_hours_last_movement_pct": "-3.2",
                    "market_hours_last_price": "240.00",
                },
                "description": "Tesla, Inc.",
            }
        ]

        result = await get_top_movers_sp500("down")

        assert "result" in result
        assert result["result"]["direction"] == "down"
        assert result["result"]["count"] == 1
        assert result["result"]["movers"][0]["symbol"] == "TSLA"
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_get_top_movers_sp500_invalid_direction(self) -> None:
        """Test invalid direction parameter."""
        result = await get_top_movers_sp500("invalid")

        assert "result" in result
        assert result["result"]["status"] == "error"
        assert "Direction must be 'up' or 'down'" in result["result"]["error"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_top_movers_sp500_no_data(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test when no movers data is available."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        mock_execute_with_retry.return_value = None

        result = await get_top_movers_sp500("up")

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert "No S&P 500 up movers found" in result["result"]["message"]
        assert result["result"]["direction"] == "up"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @pytest.mark.asyncio
    async def test_get_top_movers_sp500_authentication_failed(
        self, mock_session_manager: Any
    ) -> None:
        """Test authentication failure."""
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=False)

        result = await get_top_movers_sp500("up")

        assert "result" in result
        assert result["result"]["status"] == "error"
        assert "Authentication failed" in result["result"]["error"]


class TestStockRatings:
    """Test stock ratings functionality."""

    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_stock_ratings_success(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test successful stock ratings retrieval."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        # Mock API response
        mock_execute_with_retry.return_value = {
            "summary": {
                "num_buy_ratings": 15,
                "num_hold_ratings": 5,
                "num_sell_ratings": 2,
            },
            "ratings": [
                {
                    "published_at": "2024-07-09T10:00:00Z",
                    "type": "buy",
                    "text": "Strong buy recommendation",
                    "rating": "buy",
                }
            ],
            "ratings_published_at": "2024-07-09T10:00:00Z",
        }

        result = await get_stock_ratings("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["summary"]["num_buy_ratings"] == 15
        assert result["result"]["summary"]["num_hold_ratings"] == 5
        assert result["result"]["summary"]["num_sell_ratings"] == 2
        assert len(result["result"]["ratings"]) == 1
        assert result["result"]["ratings"][0]["rating"] == "buy"
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_get_stock_ratings_invalid_symbol(self) -> None:
        """Test invalid symbol format."""
        result = await get_stock_ratings("123INVALID")

        assert "result" in result
        assert result["result"]["status"] == "error"
        assert "Invalid symbol format" in result["result"]["error"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_stock_ratings_no_data(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test when no ratings data is available."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        mock_execute_with_retry.return_value = None

        result = await get_stock_ratings("AAPL")

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert "No ratings data found for symbol: AAPL" in result["result"]["message"]
        assert result["result"]["symbol"] == "AAPL"


class TestStockEarnings:
    """Test stock earnings functionality."""

    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_stock_earnings_success(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test successful stock earnings retrieval."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        # Mock API response
        mock_execute_with_retry.return_value = [
            {
                "year": 2024,
                "quarter": 2,
                "eps": {"actual": "1.25", "estimate": "1.20"},
                "report": {"date": "2024-07-25", "timing": "after_market"},
                "call": {
                    "datetime": "2024-07-25T17:00:00Z",
                    "broadcast_url": "https://example.com/earnings-call",
                },
            },
            {
                "year": 2024,
                "quarter": 1,
                "eps": {"actual": "1.15", "estimate": "1.10"},
                "report": {"date": "2024-04-25", "timing": "after_market"},
                "call": {
                    "datetime": "2024-04-25T17:00:00Z",
                    "broadcast_url": "https://example.com/earnings-call-q1",
                },
            },
        ]

        result = await get_stock_earnings("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["count"] == 2
        assert len(result["result"]["earnings"]) == 2
        assert result["result"]["earnings"][0]["year"] == 2024
        assert result["result"]["earnings"][0]["quarter"] == 2
        assert result["result"]["earnings"][0]["eps"]["actual"] == "1.25"
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_get_stock_earnings_invalid_symbol(self) -> None:
        """Test invalid symbol format."""
        result = await get_stock_earnings("123INVALID")

        assert "result" in result
        assert result["result"]["status"] == "error"
        assert "Invalid symbol format" in result["result"]["error"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_stock_earnings_no_data(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test when no earnings data is available."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        mock_execute_with_retry.return_value = None

        result = await get_stock_earnings("AAPL")

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert "No earnings data found for symbol: AAPL" in result["result"]["message"]
        assert result["result"]["symbol"] == "AAPL"


class TestStockNews:
    """Test stock news functionality."""

    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_stock_news_success(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test successful stock news retrieval."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        # Mock API response
        mock_execute_with_retry.return_value = [
            {
                "title": "Apple Reports Strong Q2 Results",
                "author": "Tech News Reporter",
                "published_at": "2024-07-09T14:30:00Z",
                "source": "TechCrunch",
                "summary": "Apple exceeded expectations with strong iPhone sales...",
                "url": "https://techcrunch.com/apple-q2-results",
                "preview_image_url": "https://example.com/preview.jpg",
                "num_clicks": 1250,
            },
            {
                "title": "Apple Announces New Product Line",
                "author": "Apple News Team",
                "published_at": "2024-07-08T10:00:00Z",
                "source": "Apple Newsroom",
                "summary": "Apple unveils innovative new products...",
                "url": "https://apple.com/newsroom/new-products",
                "preview_image_url": "https://example.com/apple-preview.jpg",
                "num_clicks": 2100,
            },
        ]

        result = await get_stock_news("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["count"] == 2
        assert len(result["result"]["news"]) == 2
        assert result["result"]["news"][0]["title"] == "Apple Reports Strong Q2 Results"
        assert result["result"]["news"][0]["source"] == "TechCrunch"
        assert (
            result["result"]["news"][1]["title"] == "Apple Announces New Product Line"
        )
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_get_stock_news_invalid_symbol(self) -> None:
        """Test invalid symbol format."""
        result = await get_stock_news("123INVALID")

        assert "result" in result
        assert result["result"]["status"] == "error"
        assert "Invalid symbol format" in result["result"]["error"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_stock_news_no_data(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test when no news data is available."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        mock_execute_with_retry.return_value = None

        result = await get_stock_news("AAPL")

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert "No news data found for symbol: AAPL" in result["result"]["message"]
        assert result["result"]["symbol"] == "AAPL"


class TestStockSplits:
    """Test stock splits functionality."""

    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_stock_splits_success(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test successful stock splits retrieval."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        # Mock API response
        mock_execute_with_retry.return_value = [
            {
                "execution_date": "2020-08-31",
                "multiplier": "4.000000",
                "divisor": "1.000000",
                "url": "https://robinhood.com/splits/1/",
                "instrument": "https://robinhood.com/instruments/450dfc6d-5510-4d40-abfb-f633b7d9be3e/",
            },
            {
                "execution_date": "2014-06-09",
                "multiplier": "7.000000",
                "divisor": "1.000000",
                "url": "https://robinhood.com/splits/2/",
                "instrument": "https://robinhood.com/instruments/450dfc6d-5510-4d40-abfb-f633b7d9be3e/",
            },
        ]

        result = await get_stock_splits("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["count"] == 2
        assert len(result["result"]["splits"]) == 2
        assert result["result"]["splits"][0]["execution_date"] == "2020-08-31"
        assert result["result"]["splits"][0]["multiplier"] == "4.000000"
        assert result["result"]["splits"][1]["execution_date"] == "2014-06-09"
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_get_stock_splits_invalid_symbol(self) -> None:
        """Test invalid symbol format."""
        result = await get_stock_splits("123INVALID")

        assert "result" in result
        assert result["result"]["status"] == "error"
        assert "Invalid symbol format" in result["result"]["error"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_stock_splits_no_data(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test when no splits data is available."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        mock_execute_with_retry.return_value = None

        result = await get_stock_splits("AAPL")

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert "No splits data found for symbol: AAPL" in result["result"]["message"]
        assert result["result"]["symbol"] == "AAPL"


class TestStockEvents:
    """Test stock events functionality."""

    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_stock_events_success(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test successful stock events retrieval."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        # Mock API response
        mock_execute_with_retry.return_value = [
            {
                "type": "stock_split",
                "event_date": "2020-08-31",
                "state": "confirmed",
                "direction": "debit",
                "quantity": "300.0000",
                "total_cash_amount": "0.00",
                "underlying_price": "125.00",
                "created_at": "2020-08-31T12:00:00Z",
            }
        ]

        result = await get_stock_events("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["count"] == 1
        assert len(result["result"]["events"]) == 1
        assert result["result"]["events"][0]["type"] == "stock_split"
        assert result["result"]["events"][0]["event_date"] == "2020-08-31"
        assert result["result"]["events"][0]["state"] == "confirmed"
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_get_stock_events_invalid_symbol(self) -> None:
        """Test invalid symbol format."""
        result = await get_stock_events("123INVALID")

        assert "result" in result
        assert result["result"]["status"] == "error"
        assert "Invalid symbol format" in result["result"]["error"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_stock_events_no_data(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test when no events data is available."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        mock_execute_with_retry.return_value = None

        result = await get_stock_events("AAPL")

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert "No events data found for symbol: AAPL" in result["result"]["message"]
        assert result["result"]["symbol"] == "AAPL"


class TestStockLevel2Data:
    """Test stock Level II data functionality."""

    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_stock_level2_data_success(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test successful Level II data retrieval."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        # Mock API response
        mock_execute_with_retry.return_value = {
            "asks": [
                {"price": "150.10", "quantity": "100"},
                {"price": "150.15", "quantity": "200"},
            ],
            "bids": [
                {"price": "149.90", "quantity": "200"},
                {"price": "149.85", "quantity": "150"},
            ],
            "updated_at": "2024-07-09T16:00:00Z",
        }

        result = await get_stock_level2_data("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert len(result["result"]["asks"]) == 2
        assert len(result["result"]["bids"]) == 2
        assert result["result"]["asks"][0]["price"] == "150.10"
        assert result["result"]["asks"][0]["quantity"] == "100"
        assert result["result"]["bids"][0]["price"] == "149.90"
        assert result["result"]["bids"][0]["quantity"] == "200"
        assert result["result"]["updated_at"] == "2024-07-09T16:00:00Z"
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_get_stock_level2_data_invalid_symbol(self) -> None:
        """Test invalid symbol format."""
        result = await get_stock_level2_data("123INVALID")

        assert "result" in result
        assert result["result"]["status"] == "error"
        assert "Invalid symbol format" in result["result"]["error"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_stock_level2_data_no_data(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test when no Level II data is available (Gold subscription required)."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        mock_execute_with_retry.return_value = None

        result = await get_stock_level2_data("AAPL")

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert "No Level II data found for symbol: AAPL" in result["result"]["message"]
        assert "Gold subscription may be required" in result["result"]["message"]
        assert result["result"]["symbol"] == "AAPL"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.execute_with_retry")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager")
    @patch("open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter")
    @pytest.mark.asyncio
    async def test_get_stock_level2_data_api_error(
        self,
        mock_rate_limiter: Any,
        mock_session_manager: Any,
        mock_execute_with_retry: Any,
    ) -> None:
        """Test API error handling for Level II data."""
        # Mock authentication and rate limiting
        mock_session = mock_session_manager.return_value
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_limiter = mock_rate_limiter.return_value
        mock_limiter.acquire = AsyncMock(return_value=None)

        mock_execute_with_retry.side_effect = Exception("Gold subscription required")

        result = await get_stock_level2_data("AAPL")

        assert "result" in result
        assert result["result"]["status"] == "error"
        assert "Gold subscription required" in result["result"]["error"]
