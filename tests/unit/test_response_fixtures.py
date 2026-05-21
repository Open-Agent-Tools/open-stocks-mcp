"""Tests that validate the shared API response fixture library."""

import json
from pathlib import Path
from typing import Any

import pytest

_FIXTURES_ROOT = Path(__file__).parent.parent / "fixtures" / "responses"

_REQUIRED_ROBINHOOD_FILES = [
    "quote_success.json",
    "quote_error.json",
    "fundamentals_success.json",
    "instruments_success.json",
    "markets_success.json",
    "price_history_success.json",
    "top_movers_success.json",
    "top_100_success.json",
    "market_tag_success.json",
    "trading_order_error.json",
    "instrument_search_success.json",
]

_REQUIRED_SCHWAB_FILES = [
    "quote_success.json",
    "quotes_success.json",
    "auth_error.json",
    "price_history_success.json",
    "instrument_success.json",
    "instrument_search_success.json",
    "account_numbers_success.json",
    "account_success.json",
    "accounts_success.json",
    "portfolio_success.json",
    "account_balances_success.json",
]


@pytest.mark.parametrize("filename", _REQUIRED_ROBINHOOD_FILES)
@pytest.mark.unit
@pytest.mark.journey_system
def test_robinhood_fixture_file_exists_and_parses(filename: str) -> None:
    path = _FIXTURES_ROOT / "robinhood" / filename
    assert path.exists(), f"Missing fixture: {path}"
    data = json.loads(path.read_text())
    assert data is not None


@pytest.mark.parametrize("filename", _REQUIRED_SCHWAB_FILES)
@pytest.mark.unit
@pytest.mark.journey_system
def test_schwab_fixture_file_exists_and_parses(filename: str) -> None:
    path = _FIXTURES_ROOT / "schwab" / filename
    assert path.exists(), f"Missing fixture: {path}"
    data = json.loads(path.read_text())
    assert data is not None


# Two-fixture approach to verify deep-copy isolation
@pytest.mark.unit
@pytest.mark.journey_system
def test_robinhood_quote_fixture_is_isolated(
    mock_robinhood_quote: dict[str, Any],
) -> None:
    """Mutating a returned fixture payload does not affect future requests."""
    mock_robinhood_quote["__mutated__"] = True
    assert mock_robinhood_quote.get("__mutated__") is True


@pytest.mark.unit
@pytest.mark.journey_system
def test_robinhood_quote_fixture_is_isolated_second_request(
    mock_robinhood_quote: dict[str, Any],
) -> None:
    """Second fixture request returns original payload without the mutation."""
    assert "__mutated__" not in mock_robinhood_quote


@pytest.mark.unit
@pytest.mark.journey_system
def test_schwab_auth_error_fixture_shape(
    mock_schwab_auth_error: dict[str, Any],
) -> None:
    assert "result" in mock_schwab_auth_error
    assert mock_schwab_auth_error["result"]["status"] == "error"
    assert "Not authenticated" in mock_schwab_auth_error["result"]["error"]


@pytest.mark.unit
@pytest.mark.journey_system
def test_robinhood_quote_fixture_shape(mock_robinhood_quote: dict[str, Any]) -> None:
    assert "symbol" in mock_robinhood_quote
    assert "last_trade_price" in mock_robinhood_quote
    assert "bid_price" in mock_robinhood_quote
    assert "ask_price" in mock_robinhood_quote


@pytest.mark.unit
@pytest.mark.journey_system
def test_schwab_quote_fixture_shape(mock_schwab_quote: dict[str, Any]) -> None:
    assert "AAPL" in mock_schwab_quote
    assert "quote" in mock_schwab_quote["AAPL"]
    assert "lastPrice" in mock_schwab_quote["AAPL"]["quote"]


@pytest.mark.unit
@pytest.mark.journey_system
def test_schwab_quotes_fixture_shape(mock_schwab_quotes: dict[str, Any]) -> None:
    assert "AAPL" in mock_schwab_quotes
    assert "GOOGL" in mock_schwab_quotes
    assert "lastPrice" in mock_schwab_quotes["AAPL"]["quote"]


@pytest.mark.unit
@pytest.mark.journey_system
def test_robinhood_instruments_fixture_shape(
    mock_robinhood_instruments: list[dict[str, Any]],
) -> None:
    assert len(mock_robinhood_instruments) == 2
    assert mock_robinhood_instruments[0]["symbol"] == "AAPL"
    assert mock_robinhood_instruments[1]["symbol"] == "GOOGL"


@pytest.mark.unit
@pytest.mark.journey_system
def test_schwab_account_numbers_fixture_shape(
    mock_schwab_account_numbers: list[dict[str, Any]],
) -> None:
    assert len(mock_schwab_account_numbers) == 2
    assert "accountNumber" in mock_schwab_account_numbers[0]
    assert "hashValue" in mock_schwab_account_numbers[0]


@pytest.mark.unit
@pytest.mark.journey_system
def test_schwab_portfolio_fixture_shape(mock_schwab_portfolio: dict[str, Any]) -> None:
    assert "securitiesAccount" in mock_schwab_portfolio
    positions = mock_schwab_portfolio["securitiesAccount"]["positions"]
    assert len(positions) == 1
    assert positions[0]["instrument"]["symbol"] == "AAPL"


@pytest.mark.unit
@pytest.mark.journey_system
def test_schwab_account_balances_fixture_shape(
    mock_schwab_account_balances: dict[str, Any],
) -> None:
    assert "securitiesAccount" in mock_schwab_account_balances
    balances = mock_schwab_account_balances["securitiesAccount"]["currentBalances"]
    assert balances["liquidationValue"] == 50000.0
    assert balances["cashBalance"] == 10000.0


@pytest.mark.unit
@pytest.mark.journey_system
def test_robinhood_price_history_fixture_shape(
    mock_robinhood_price_history: list[dict[str, Any]],
) -> None:
    assert len(mock_robinhood_price_history) == 2
    assert "begins_at" in mock_robinhood_price_history[0]
    assert "close_price" in mock_robinhood_price_history[0]


@pytest.mark.unit
@pytest.mark.journey_system
def test_schwab_price_history_fixture_shape(
    mock_schwab_price_history: dict[str, Any],
) -> None:
    assert "candles" in mock_schwab_price_history
    assert len(mock_schwab_price_history["candles"]) == 2
    assert "close" in mock_schwab_price_history["candles"][0]
