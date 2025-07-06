"""Shared pytest fixtures for open-stocks-mcp tests."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_robin_stocks() -> MagicMock:
    """Mock robin_stocks module for testing."""
    mock_rh = MagicMock()
    mock_rh.stocks.get_latest_price.return_value = ["100.50"]
    mock_rh.profiles.load_portfolio_profile.return_value = {
        "total_return_today": "25.50",
        "market_value": "1000.00",
    }
    return mock_rh


@pytest.fixture
def sample_stock_data() -> dict[str, float | int | str]:
    """Sample stock data for testing."""
    return {
        "symbol": "AAPL",
        "price": 150.25,
        "change": 2.50,
        "change_percent": 1.69,
        "volume": 50000000,
    }


@pytest.fixture
def sample_portfolio_data() -> dict[str, str]:
    """Sample portfolio data for testing."""
    return {
        "total_return_today": "25.50",
        "market_value": "1000.00",
        "total_return_today_percent": "2.61",
        "day_trade_buying_power": "0.00",
    }
