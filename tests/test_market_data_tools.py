"""Tests for Robin Stocks advanced market data tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.robinhood_market_data_tools import (
    get_stock_earnings,
    get_stock_events,
    get_stock_level2_data,
    get_stock_news,
    get_stock_ratings,
    get_stock_splits,
    get_stocks_by_tag,
    get_top_100,
    get_top_movers,
    get_top_movers_sp500,
)


@pytest.fixture
def mock_session_manager():
    """Mock session manager for tests."""
    with patch(
        "open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager"
    ) as mock:
        session_mgr = MagicMock()
        session_mgr.ensure_authenticated = AsyncMock(return_value=True)
        mock.return_value = session_mgr
        yield mock


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter for tests."""
    with patch(
        "open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter"
    ) as mock:
        limiter = MagicMock()
        limiter.acquire = AsyncMock()
        mock.return_value = limiter
        yield mock


@pytest.mark.asyncio
async def test_get_top_movers_sp500_up_success(mock_session_manager, mock_rate_limiter):
    """Test successful S&P 500 up movers retrieval."""
    mock_movers_data = [
        {
            "symbol": "AAPL",
            "instrument_url": "https://api.robinhood.com/instruments/123/",
            "updated_at": "2024-07-09T16:00:00Z",
            "price_movement": {
                "market_hours_last_movement_pct": "2.5",
                "market_hours_last_price": "150.00",
            },
            "description": "Apple Inc.",
        },
        {
            "symbol": "MSFT",
            "instrument_url": "https://api.robinhood.com/instruments/456/",
            "updated_at": "2024-07-09T16:00:00Z",
            "price_movement": {
                "market_hours_last_movement_pct": "1.8",
                "market_hours_last_price": "300.00",
            },
            "description": "Microsoft Corporation",
        },
    ]

    with patch(
        "robin_stocks.robinhood.get_top_movers_sp500", return_value=mock_movers_data
    ):
        result = await get_top_movers_sp500("up")

    assert result["result"]["status"] == "success"
    assert result["result"]["direction"] == "up"
    assert result["result"]["count"] == 2
    assert len(result["result"]["movers"]) == 2
    assert result["result"]["movers"][0]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_get_top_movers_sp500_down_success(
    mock_session_manager, mock_rate_limiter
):
    """Test successful S&P 500 down movers retrieval."""
    mock_movers_data = [
        {
            "symbol": "TSLA",
            "instrument_url": "https://api.robinhood.com/instruments/789/",
            "updated_at": "2024-07-09T16:00:00Z",
            "price_movement": {
                "market_hours_last_movement_pct": "-3.2",
                "market_hours_last_price": "200.00",
            },
            "description": "Tesla Inc.",
        }
    ]

    with patch(
        "robin_stocks.robinhood.get_top_movers_sp500", return_value=mock_movers_data
    ):
        result = await get_top_movers_sp500("down")

    assert result["result"]["status"] == "success"
    assert result["result"]["direction"] == "down"
    assert result["result"]["count"] == 1
    assert result["result"]["movers"][0]["symbol"] == "TSLA"


@pytest.mark.asyncio
async def test_get_top_movers_sp500_invalid_direction(
    mock_session_manager, mock_rate_limiter
):
    """Test S&P 500 movers with invalid direction."""
    result = await get_top_movers_sp500("sideways")

    assert result["result"]["status"] == "error"
    assert "Direction must be 'up' or 'down'" in result["result"]["error"]


@pytest.mark.asyncio
async def test_get_top_100_success(mock_session_manager, mock_rate_limiter):
    """Test successful top 100 stocks retrieval."""
    mock_stocks_data = [
        {
            "symbol": "AAPL",
            "last_trade_price": "150.00",
            "previous_close": "149.50",
            "ask_price": "150.10",
            "bid_price": "149.90",
            "updated_at": "2024-07-09T16:00:00Z",
            "trading_halted": False,
            "has_traded": True,
        },
        {
            "symbol": "GOOGL",
            "last_trade_price": "2500.00",
            "previous_close": "2495.00",
            "ask_price": "2501.00",
            "bid_price": "2499.00",
            "updated_at": "2024-07-09T16:00:00Z",
            "trading_halted": False,
            "has_traded": True,
        },
    ]

    with patch("robin_stocks.robinhood.get_top_100", return_value=mock_stocks_data):
        result = await get_top_100()

    assert result["result"]["status"] == "success"
    assert result["result"]["count"] == 2
    assert len(result["result"]["stocks"]) == 2
    assert result["result"]["stocks"][0]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_get_top_movers_success(mock_session_manager, mock_rate_limiter):
    """Test successful top movers retrieval."""
    mock_movers_data = [
        {
            "symbol": "GME",
            "last_trade_price": "25.00",
            "previous_close": "20.00",
            "ask_price": "25.10",
            "bid_price": "24.90",
            "updated_at": "2024-07-09T16:00:00Z",
            "trading_halted": False,
            "has_traded": True,
        }
    ]

    with patch("robin_stocks.robinhood.get_top_movers", return_value=mock_movers_data):
        result = await get_top_movers()

    assert result["result"]["status"] == "success"
    assert result["result"]["count"] == 1
    assert len(result["result"]["movers"]) == 1
    assert result["result"]["movers"][0]["symbol"] == "GME"


@pytest.mark.asyncio
async def test_get_stocks_by_tag_success(mock_session_manager, mock_rate_limiter):
    """Test successful stocks by tag retrieval."""
    mock_stocks_data = [
        {
            "symbol": "AAPL",
            "last_trade_price": "150.00",
            "previous_close": "149.50",
            "ask_price": "150.10",
            "bid_price": "149.90",
            "updated_at": "2024-07-09T16:00:00Z",
        },
        {
            "symbol": "MSFT",
            "last_trade_price": "300.00",
            "previous_close": "299.00",
            "ask_price": "300.10",
            "bid_price": "299.90",
            "updated_at": "2024-07-09T16:00:00Z",
        },
    ]

    with patch(
        "robin_stocks.robinhood.get_all_stocks_from_market_tag",
        return_value=mock_stocks_data,
    ):
        result = await get_stocks_by_tag("technology")

    assert result["result"]["status"] == "success"
    assert result["result"]["tag"] == "technology"
    assert result["result"]["count"] == 2
    assert len(result["result"]["stocks"]) == 2
    assert result["result"]["stocks"][0]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_get_stocks_by_tag_invalid_tag(mock_session_manager, mock_rate_limiter):
    """Test stocks by tag with invalid tag."""
    result = await get_stocks_by_tag("")

    assert result["result"]["status"] == "error"
    assert "Tag parameter is required" in result["result"]["error"]


@pytest.mark.asyncio
async def test_get_stock_ratings_success(mock_session_manager, mock_rate_limiter):
    """Test successful stock ratings retrieval."""
    mock_ratings_data = {
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

    with patch("robin_stocks.robinhood.get_ratings", return_value=mock_ratings_data):
        result = await get_stock_ratings("AAPL")

    assert result["result"]["status"] == "success"
    assert result["result"]["symbol"] == "AAPL"
    assert result["result"]["summary"]["num_buy_ratings"] == 15
    assert len(result["result"]["ratings"]) == 1


@pytest.mark.asyncio
async def test_get_stock_earnings_success(mock_session_manager, mock_rate_limiter):
    """Test successful stock earnings retrieval."""
    mock_earnings_data = [
        {
            "year": 2024,
            "quarter": 2,
            "eps": {"actual": "1.25", "estimate": "1.20"},
            "report": {"date": "2024-07-25", "timing": "after_market"},
            "call": {
                "datetime": "2024-07-25T17:00:00Z",
                "broadcast_url": "https://example.com",
            },
        }
    ]

    with patch("robin_stocks.robinhood.get_earnings", return_value=mock_earnings_data):
        result = await get_stock_earnings("AAPL")

    assert result["result"]["status"] == "success"
    assert result["result"]["symbol"] == "AAPL"
    assert result["result"]["count"] == 1
    assert len(result["result"]["earnings"]) == 1
    assert result["result"]["earnings"][0]["year"] == 2024


@pytest.mark.asyncio
async def test_get_stock_news_success(mock_session_manager, mock_rate_limiter):
    """Test successful stock news retrieval."""
    mock_news_data = [
        {
            "title": "Apple Reports Strong Q2 Results",
            "author": "Tech News Reporter",
            "published_at": "2024-07-09T14:30:00Z",
            "source": "TechCrunch",
            "summary": "Apple exceeded expectations...",
            "url": "https://example.com/news",
            "preview_image_url": "https://example.com/image.jpg",
            "num_clicks": 1250,
        }
    ]

    with patch("robin_stocks.robinhood.get_news", return_value=mock_news_data):
        result = await get_stock_news("AAPL")

    assert result["result"]["status"] == "success"
    assert result["result"]["symbol"] == "AAPL"
    assert result["result"]["count"] == 1
    assert len(result["result"]["news"]) == 1
    assert result["result"]["news"][0]["title"] == "Apple Reports Strong Q2 Results"


@pytest.mark.asyncio
async def test_get_stock_splits_success(mock_session_manager, mock_rate_limiter):
    """Test successful stock splits retrieval."""
    mock_splits_data = [
        {
            "execution_date": "2020-08-31",
            "multiplier": "4.000000",
            "divisor": "1.000000",
            "url": "https://api.robinhood.com/splits/123/",
            "instrument": "https://api.robinhood.com/instruments/456/",
        }
    ]

    with patch("robin_stocks.robinhood.get_splits", return_value=mock_splits_data):
        result = await get_stock_splits("AAPL")

    assert result["result"]["status"] == "success"
    assert result["result"]["symbol"] == "AAPL"
    assert result["result"]["count"] == 1
    assert len(result["result"]["splits"]) == 1
    assert result["result"]["splits"][0]["execution_date"] == "2020-08-31"


@pytest.mark.asyncio
async def test_get_stock_events_success(mock_session_manager, mock_rate_limiter):
    """Test successful stock events retrieval."""
    mock_events_data = [
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

    with patch("robin_stocks.robinhood.get_events", return_value=mock_events_data):
        result = await get_stock_events("AAPL")

    assert result["result"]["status"] == "success"
    assert result["result"]["symbol"] == "AAPL"
    assert result["result"]["count"] == 1
    assert len(result["result"]["events"]) == 1
    assert result["result"]["events"][0]["type"] == "stock_split"


@pytest.mark.asyncio
async def test_get_stock_level2_data_success(mock_session_manager, mock_rate_limiter):
    """Test successful Level II data retrieval."""
    mock_level2_data = {
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

    with patch(
        "robin_stocks.robinhood.get_pricebook_by_symbol", return_value=mock_level2_data
    ):
        result = await get_stock_level2_data("AAPL")

    assert result["result"]["status"] == "success"
    assert result["result"]["symbol"] == "AAPL"
    assert len(result["result"]["asks"]) == 2
    assert len(result["result"]["bids"]) == 2
    assert result["result"]["asks"][0]["price"] == "150.10"


@pytest.mark.asyncio
async def test_invalid_symbol_validation():
    """Test various functions with invalid symbols."""
    invalid_symbols = ["", "TOOLONG", "123456"]

    functions_to_test = [
        get_stock_ratings,
        get_stock_earnings,
        get_stock_news,
        get_stock_splits,
        get_stock_events,
        get_stock_level2_data,
    ]

    # Mock authentication to pass so we can test symbol validation
    with patch(
        "open_stocks_mcp.tools.robinhood_market_data_tools.get_session_manager"
    ) as mock_session:
        session_mgr = MagicMock()
        session_mgr.ensure_authenticated = AsyncMock(return_value=True)
        mock_session.return_value = session_mgr

        with patch(
            "open_stocks_mcp.tools.robinhood_market_data_tools.get_rate_limiter"
        ) as mock_limiter:
            limiter = MagicMock()
            limiter.acquire = AsyncMock()
            mock_limiter.return_value = limiter

            for func in functions_to_test:
                for invalid_symbol in invalid_symbols:
                    result = await func(invalid_symbol)
                    assert result["result"]["status"] == "error"
                    assert "Invalid symbol format" in result["result"]["error"]


@pytest.mark.asyncio
async def test_no_data_scenarios(mock_session_manager, mock_rate_limiter):
    """Test functions when no data is returned."""
    functions_and_patches = [
        (get_top_movers_sp500, "robin_stocks.robinhood.get_top_movers_sp500", "up"),
        (get_top_100, "robin_stocks.robinhood.get_top_100", None),
        (get_top_movers, "robin_stocks.robinhood.get_top_movers", None),
        (
            get_stocks_by_tag,
            "robin_stocks.robinhood.get_all_stocks_from_market_tag",
            "technology",
        ),
        (get_stock_ratings, "robin_stocks.robinhood.get_ratings", "AAPL"),
        (get_stock_earnings, "robin_stocks.robinhood.get_earnings", "AAPL"),
        (get_stock_news, "robin_stocks.robinhood.get_news", "AAPL"),
        (get_stock_splits, "robin_stocks.robinhood.get_splits", "AAPL"),
        (get_stock_events, "robin_stocks.robinhood.get_events", "AAPL"),
        (
            get_stock_level2_data,
            "robin_stocks.robinhood.get_pricebook_by_symbol",
            "AAPL",
        ),
    ]

    for func, patch_target, param in functions_and_patches:
        with patch(patch_target, return_value=None):
            if param:
                result = await func(param)
            else:
                result = await func()

            assert result["result"]["status"] == "no_data"


@pytest.mark.asyncio
async def test_api_error_handling(mock_session_manager, mock_rate_limiter):
    """Test error handling when API calls fail."""
    functions_and_patches = [
        (get_top_movers_sp500, "robin_stocks.robinhood.get_top_movers_sp500", "up"),
        (get_top_100, "robin_stocks.robinhood.get_top_100", None),
        (get_top_movers, "robin_stocks.robinhood.get_top_movers", None),
        (
            get_stocks_by_tag,
            "robin_stocks.robinhood.get_all_stocks_from_market_tag",
            "technology",
        ),
        (get_stock_ratings, "robin_stocks.robinhood.get_ratings", "AAPL"),
        (get_stock_earnings, "robin_stocks.robinhood.get_earnings", "AAPL"),
        (get_stock_news, "robin_stocks.robinhood.get_news", "AAPL"),
        (get_stock_splits, "robin_stocks.robinhood.get_splits", "AAPL"),
        (get_stock_events, "robin_stocks.robinhood.get_events", "AAPL"),
        (
            get_stock_level2_data,
            "robin_stocks.robinhood.get_pricebook_by_symbol",
            "AAPL",
        ),
    ]

    for func, patch_target, param in functions_and_patches:
        with patch(patch_target, side_effect=Exception("API Error")):
            if param:
                result = await func(param)
            else:
                result = await func()

            assert result["result"]["status"] == "error"
            assert "API Error" in result["result"]["error"]
