"""Tests for Robin Stocks dividend and income tracking tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.robinhood_dividend_tools import (
    get_dividends,
    get_dividends_by_instrument,
    get_interest_payments,
    get_stock_loan_payments,
    get_total_dividends,
)


@pytest.fixture
def mock_session_manager():
    """Mock session manager for tests."""
    with patch(
        "open_stocks_mcp.tools.robinhood_dividend_tools.get_session_manager"
    ) as mock:
        session_mgr = MagicMock()
        session_mgr.ensure_authenticated = AsyncMock(return_value=True)
        mock.return_value = session_mgr
        yield mock


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter for tests."""
    with patch(
        "open_stocks_mcp.tools.robinhood_dividend_tools.get_rate_limiter"
    ) as mock:
        limiter = MagicMock()
        limiter.acquire = AsyncMock()
        mock.return_value = limiter
        yield mock


@pytest.mark.asyncio
async def test_get_dividends_success(mock_session_manager, mock_rate_limiter):
    """Test successful dividend retrieval."""
    mock_dividend_data = [
        {
            "id": "div1",
            "amount": "2.50",
            "state": "paid",
            "paid_at": "2024-02-15T00:00:00Z",
            "position": "10.0",
            "rate": "0.25",
            "withholding": "0.00",
            "instrument": "https://api.robinhood.com/instruments/123/",
            "account": "acc123",
            "record_date": "2024-02-01T00:00:00Z",
            "payable_date": "2024-02-15T00:00:00Z",
        },
        {
            "id": "div2",
            "amount": "3.00",
            "state": "paid",
            "paid_at": "2024-05-15T00:00:00Z",
            "position": "12.0",
            "rate": "0.25",
            "withholding": "0.00",
            "instrument": "https://api.robinhood.com/instruments/456/",
            "account": "acc123",
            "record_date": "2024-05-01T00:00:00Z",
            "payable_date": "2024-05-15T00:00:00Z",
        },
    ]

    mock_instrument_data = {"symbol": "AAPL", "simple_name": "Apple"}

    with (
        patch(
            "robin_stocks.robinhood.account.get_dividends",
            return_value=mock_dividend_data,
        ),
        patch(
            "robin_stocks.robinhood.stocks.get_instrument_by_url",
            return_value=mock_instrument_data,
        ),
    ):
        result = await get_dividends()

    assert result["result"]["status"] == "success"
    assert result["result"]["count"] == 2
    assert result["result"]["total_dividends"] == "5.50"
    assert len(result["result"]["dividends"]) == 2
    assert result["result"]["dividends"][0]["symbol"] == "AAPL"
    assert result["result"]["dividends"][0]["amount"] == "2.50"


@pytest.mark.asyncio
async def test_get_dividends_no_auth(mock_rate_limiter):
    """Test dividend retrieval without authentication."""
    with patch(
        "open_stocks_mcp.tools.robinhood_dividend_tools.get_session_manager"
    ) as mock:
        session_mgr = MagicMock()
        session_mgr.ensure_authenticated = AsyncMock(return_value=False)
        mock.return_value = session_mgr

        result = await get_dividends()

    assert result["result"]["status"] == "error"
    assert "Authentication required" in result["result"]["error"]


@pytest.mark.asyncio
async def test_get_total_dividends_success(mock_session_manager, mock_rate_limiter):
    """Test successful total dividends retrieval."""
    mock_dividend_data = [
        {
            "amount": "100.00",
            "state": "paid",
            "paid_at": "2023-02-15T00:00:00Z",
        },
        {
            "amount": "150.00",
            "state": "paid",
            "paid_at": "2024-05-15T00:00:00Z",
        },
        {
            "amount": "50.00",
            "state": "pending",
            "paid_at": "2024-12-15T00:00:00Z",
        },
    ]

    with (
        patch(
            "robin_stocks.robinhood.account.get_total_dividends", return_value="250.00"
        ),
        patch(
            "robin_stocks.robinhood.account.get_dividends",
            return_value=mock_dividend_data,
        ),
    ):
        result = await get_total_dividends()

    assert result["result"]["status"] == "success"
    assert result["result"]["total_amount"] == "250.00"
    assert result["result"]["payment_count"] == 2  # Only paid dividends
    assert result["result"]["by_year"]["2023"] == "100.00"
    assert result["result"]["by_year"]["2024"] == "150.00"
    assert result["result"]["first_payment_date"] == "2023-02-15T00:00:00Z"
    assert result["result"]["last_payment_date"] == "2024-05-15T00:00:00Z"


@pytest.mark.asyncio
async def test_get_dividends_by_instrument_success(
    mock_session_manager, mock_rate_limiter
):
    """Test successful dividend retrieval by instrument."""
    mock_dividend_data = [
        {
            "id": "div1",
            "amount": "2.20",
            "state": "paid",
            "paid_at": "2024-02-15T00:00:00Z",
            "position": "10.0",
            "rate": "0.22",
            "withholding": "0.00",
            "record_date": "2024-02-01T00:00:00Z",
            "payable_date": "2024-02-15T00:00:00Z",
        }
    ]

    with patch(
        "robin_stocks.robinhood.account.get_dividends_by_instrument",
        return_value=mock_dividend_data,
    ):
        result = await get_dividends_by_instrument("AAPL")

    assert result["result"]["status"] == "success"
    assert result["result"]["symbol"] == "AAPL"
    assert result["result"]["count"] == 1
    assert result["result"]["total_amount"] == "2.20"
    assert result["result"]["dividends"][0]["amount"] == "2.20"


@pytest.mark.asyncio
async def test_get_dividends_by_instrument_invalid_symbol(
    mock_session_manager, mock_rate_limiter
):
    """Test dividend retrieval with invalid symbol."""
    result = await get_dividends_by_instrument("")

    assert result["result"]["status"] == "error"
    assert "Symbol parameter is required" in result["result"]["error"]


@pytest.mark.asyncio
async def test_get_interest_payments_success(mock_session_manager, mock_rate_limiter):
    """Test successful interest payment retrieval."""
    mock_interest_data = [
        {
            "id": "int1",
            "amount": "1.23",
            "paid_at": "2024-12-01T00:00:00Z",
            "type": "cash_management",
            "rate": "0.50",
            "state": "paid",
            "created_at": "2024-12-01T00:00:00Z",
        },
        {
            "id": "int2",
            "amount": "1.45",
            "paid_at": "2024-11-01T00:00:00Z",
            "type": "cash_management",
            "rate": "0.50",
            "state": "paid",
            "created_at": "2024-11-01T00:00:00Z",
        },
    ]

    with patch(
        "robin_stocks.robinhood.account.get_interest_payments",
        return_value=mock_interest_data,
    ):
        result = await get_interest_payments()

    assert result["result"]["status"] == "success"
    assert result["result"]["count"] == 2
    assert result["result"]["total_interest"] == "2.68"
    assert len(result["result"]["interest_payments"]) == 2
    assert result["result"]["interest_payments"][0]["type"] == "cash_management"


@pytest.mark.asyncio
async def test_get_stock_loan_payments_success(mock_session_manager, mock_rate_limiter):
    """Test successful stock loan payment retrieval."""
    mock_loan_data = [
        {
            "id": "loan1",
            "amount": "0.45",
            "paid_at": "2024-12-01T00:00:00Z",
            "state": "paid",
            "shares_loaned": "100",
            "rate": "0.0045",
            "instrument": "https://api.robinhood.com/instruments/789/",
            "created_at": "2024-12-01T00:00:00Z",
        }
    ]

    mock_instrument_data = {"symbol": "AMC", "simple_name": "AMC Entertainment"}

    with (
        patch(
            "robin_stocks.robinhood.account.get_stock_loan_payments",
            return_value=mock_loan_data,
        ),
        patch(
            "robin_stocks.robinhood.stocks.get_instrument_by_url",
            return_value=mock_instrument_data,
        ),
    ):
        result = await get_stock_loan_payments()

    assert result["result"]["status"] == "success"
    assert result["result"]["count"] == 1
    assert result["result"]["total_loan_income"] == "0.45"
    assert result["result"]["enrolled"] is True
    assert result["result"]["loan_payments"][0]["symbol"] == "AMC"
    assert result["result"]["loan_payments"][0]["shares_loaned"] == "100"


@pytest.mark.asyncio
async def test_get_stock_loan_payments_not_enrolled(
    mock_session_manager, mock_rate_limiter
):
    """Test stock loan payments when not enrolled."""
    with patch(
        "robin_stocks.robinhood.account.get_stock_loan_payments", return_value=[]
    ):
        result = await get_stock_loan_payments()

    assert result["result"]["status"] == "success"
    assert result["result"]["count"] == 0
    assert result["result"]["total_loan_income"] == "0.00"
    assert result["result"]["enrolled"] is False


@pytest.mark.asyncio
async def test_get_dividends_api_error(mock_session_manager, mock_rate_limiter):
    """Test dividend retrieval with API error."""
    with patch(
        "robin_stocks.robinhood.account.get_dividends",
        side_effect=Exception("API Error"),
    ):
        result = await get_dividends()

    assert result["result"]["status"] == "error"
    assert "API Error" in result["result"]["error"]


@pytest.mark.asyncio
async def test_get_total_dividends_no_data(mock_session_manager, mock_rate_limiter):
    """Test total dividends with no dividend data."""
    with (
        patch("robin_stocks.robinhood.account.get_total_dividends", return_value=None),
        patch("robin_stocks.robinhood.account.get_dividends", return_value=[]),
    ):
        result = await get_total_dividends()

    assert result["result"]["status"] == "success"
    assert result["result"]["total_amount"] == "0.00"
    assert result["result"]["payment_count"] == 0
    assert result["result"]["by_year"] == {}
