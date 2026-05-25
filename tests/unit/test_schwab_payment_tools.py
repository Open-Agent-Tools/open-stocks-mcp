import datetime
from unittest.mock import MagicMock, patch

import pytest

from open_stocks_mcp.tools.schwab_payment_tools import (
    _classify_transaction,
    schwab_get_dividends,
    schwab_get_dividends_by_symbol,
)


def test_classify_transaction_dividend_returns_dividend():
    tx = {"type": "DIVIDEND_OR_INTEREST", "description": "QUALIFIED DIVIDEND"}
    assert _classify_transaction(tx) == "dividend"


def test_classify_transaction_interest_returns_interest():
    tx = {
        "type": "DIVIDEND_OR_INTEREST",
        "description": "FREE BALANCE INTEREST ADJUSTMENT",
    }
    assert _classify_transaction(tx) == "interest"


def test_classify_transaction_journal_stock_loan_returns_stock_loan():
    tx = {"type": "JOURNAL", "description": "SECURITIES LENDING REVENUE"}
    assert _classify_transaction(tx) == "stock_loan"


def test_classify_transaction_other_returns_other():
    tx = {"type": "TRADE", "description": "Bought AAPL"}
    assert _classify_transaction(tx) == "other"


def test_classify_transaction_missing_fields_returns_other():
    assert _classify_transaction({}) == "other"


@pytest.mark.asyncio
@patch("open_stocks_mcp.tools.schwab_payment_tools.get_authenticated_broker_or_error")
@patch("open_stocks_mcp.tools.schwab_payment_tools.asyncio.to_thread")
async def test_schwab_get_dividends_success(mock_to_thread, mock_get_broker):
    # Mock broker
    broker = MagicMock()
    mock_get_broker.return_value = (broker, None)

    # Mock transactions
    mock_to_thread.return_value = [
        {
            "type": "DIVIDEND_OR_INTEREST",
            "description": "QUALIFIED DIVIDEND",
            "netAmount": 1.50,
        },
        {"type": "DIVIDEND_OR_INTEREST", "description": "DIVIDEND", "netAmount": 2.50},
        {
            "type": "DIVIDEND_OR_INTEREST",
            "description": "FREE BALANCE INTEREST ADJUSTMENT",
            "netAmount": 0.05,
        },
        {"type": "TRADE", "description": "Bought AAPL", "netAmount": 100.0},
    ]

    result = await schwab_get_dividends("hash123")

    assert result["result"]["status"] == "success"
    assert len(result["result"]["dividends"]) == 2
    assert result["result"]["total_amount"] == "4.00"
    assert result["result"]["count"] == 2
    assert result["result"]["dividends"][0]["netAmount"] == 1.50
    assert result["result"]["dividends"][1]["netAmount"] == 2.50


@pytest.mark.asyncio
@patch("open_stocks_mcp.tools.schwab_payment_tools.get_authenticated_broker_or_error")
@patch("open_stocks_mcp.tools.schwab_payment_tools.asyncio.to_thread")
async def test_schwab_get_dividends_passes_dividend_or_interest_type_filter(
    mock_to_thread, mock_get_broker
):
    broker = MagicMock()
    mock_get_broker.return_value = (broker, None)
    mock_to_thread.return_value = []

    await schwab_get_dividends("hash123")

    mock_to_thread.assert_called_once()
    _, kwargs = mock_to_thread.call_args
    assert kwargs["transaction_types"] == ["DIVIDEND_OR_INTEREST"]


@pytest.mark.asyncio
@patch("open_stocks_mcp.tools.schwab_payment_tools.get_authenticated_broker_or_error")
@patch("open_stocks_mcp.tools.schwab_payment_tools.asyncio.to_thread")
async def test_schwab_get_dividends_passes_date_filters(
    mock_to_thread, mock_get_broker
):
    broker = MagicMock()
    mock_get_broker.return_value = (broker, None)
    mock_to_thread.return_value = []

    await schwab_get_dividends(
        "hash123", start_date="2026-04-01", end_date="2026-04-30"
    )

    mock_to_thread.assert_called_once()
    _, kwargs = mock_to_thread.call_args
    assert kwargs["start_date"] == datetime.date(2026, 4, 1)
    assert kwargs["end_date"] == datetime.date(2026, 4, 30)


@pytest.mark.asyncio
@patch("open_stocks_mcp.tools.schwab_payment_tools.get_authenticated_broker_or_error")
@patch("open_stocks_mcp.tools.schwab_payment_tools.asyncio.to_thread")
async def test_schwab_get_dividends_empty_list(mock_to_thread, mock_get_broker):
    broker = MagicMock()
    mock_get_broker.return_value = (broker, None)
    mock_to_thread.return_value = []

    result = await schwab_get_dividends("hash123")

    assert result["result"]["status"] == "success"
    assert result["result"]["dividends"] == []
    assert result["result"]["total_amount"] == "0.00"
    assert result["result"]["count"] == 0


@pytest.mark.asyncio
@patch("open_stocks_mcp.tools.schwab_payment_tools.get_authenticated_broker_or_error")
@patch("open_stocks_mcp.tools.schwab_payment_tools.asyncio.to_thread")
async def test_schwab_get_dividends_auth_error(mock_to_thread, mock_get_broker):
    mock_get_broker.return_value = (
        None,
        {"result": {"status": "error", "error": "Auth failed"}},
    )

    result = await schwab_get_dividends("hash123")

    assert result["result"]["status"] == "error"
    assert result["result"]["error"] == "Auth failed"
    mock_to_thread.assert_not_called()


@pytest.mark.asyncio
@patch("open_stocks_mcp.tools.schwab_payment_tools.get_authenticated_broker_or_error")
@patch("open_stocks_mcp.tools.schwab_payment_tools.asyncio.to_thread")
async def test_schwab_get_dividends_by_symbol_passes_symbol_to_client(
    mock_to_thread, mock_get_broker
):
    broker = MagicMock()
    mock_get_broker.return_value = (broker, None)
    mock_to_thread.return_value = []

    await schwab_get_dividends_by_symbol("abc123", "AAPL")

    mock_to_thread.assert_called_once()
    _, kwargs = mock_to_thread.call_args
    assert kwargs["symbol"] == "AAPL"
    assert kwargs["transaction_types"] == ["DIVIDEND_OR_INTEREST"]


@pytest.mark.asyncio
@patch("open_stocks_mcp.tools.schwab_payment_tools.get_authenticated_broker_or_error")
@patch("open_stocks_mcp.tools.schwab_payment_tools.asyncio.to_thread")
async def test_schwab_get_dividends_by_symbol_returns_symbol_in_result(
    mock_to_thread, mock_get_broker
):
    broker = MagicMock()
    mock_get_broker.return_value = (broker, None)
    mock_to_thread.return_value = []

    result = await schwab_get_dividends_by_symbol("abc123", "AAPL")

    assert result["result"]["symbol"] == "AAPL"


@pytest.mark.asyncio
@patch("open_stocks_mcp.tools.schwab_payment_tools.get_authenticated_broker_or_error")
@patch("open_stocks_mcp.tools.schwab_payment_tools.asyncio.to_thread")
async def test_schwab_get_dividends_by_symbol_filters_classification_to_dividend_only(
    mock_to_thread, mock_get_broker
):
    broker = MagicMock()
    mock_get_broker.return_value = (broker, None)
    mock_to_thread.return_value = [
        {
            "type": "DIVIDEND_OR_INTEREST",
            "description": "QUALIFIED DIVIDEND",
            "netAmount": 1.50,
            "symbol": "AAPL",
        },
        {
            "type": "DIVIDEND_OR_INTEREST",
            "description": "FREE BALANCE INTEREST ADJUSTMENT",
            "netAmount": 0.05,
            "symbol": "AAPL",
        },
    ]

    result = await schwab_get_dividends_by_symbol("abc123", "AAPL")

    assert result["result"]["count"] == 1
    assert len(result["result"]["dividends"]) == 1
    assert result["result"]["dividends"][0]["description"] == "QUALIFIED DIVIDEND"


@pytest.mark.asyncio
@patch("open_stocks_mcp.tools.schwab_payment_tools.get_authenticated_broker_or_error")
@patch("open_stocks_mcp.tools.schwab_payment_tools.asyncio.to_thread")
async def test_schwab_get_dividends_by_symbol_uppercases_symbol(
    mock_to_thread, mock_get_broker
):
    broker = MagicMock()
    mock_get_broker.return_value = (broker, None)
    mock_to_thread.return_value = []

    result = await schwab_get_dividends_by_symbol("abc123", "aapl")

    _, kwargs = mock_to_thread.call_args
    assert kwargs["symbol"] == "AAPL"
    assert result["result"]["symbol"] == "AAPL"
