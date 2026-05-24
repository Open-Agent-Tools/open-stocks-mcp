"""Contract tests for shared broker response fixtures."""

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "responses"

REQUIRED_FIXTURE_PATHS = [
    "robinhood/quote_success.json",
    "robinhood/quote_error.json",
    "robinhood/fundamentals_success.json",
    "robinhood/instruments_success.json",
    "robinhood/markets_success.json",
    "robinhood/price_history_success.json",
    "robinhood/top_movers_success.json",
    "robinhood/top_100_success.json",
    "robinhood/market_tag_success.json",
    "robinhood/trading_order_error.json",
    "schwab/quote_success.json",
    "schwab/quotes_success.json",
    "schwab/auth_error.json",
    "schwab/price_history_success.json",
    "schwab/instrument_success.json",
    "schwab/instrument_search_success.json",
    "schwab/account_numbers_success.json",
    "schwab/account_success.json",
    "schwab/accounts_success.json",
    "schwab/portfolio_success.json",
    "schwab/account_balances_success.json",
]

REQUIRED_FIXTURE_NAMES = [
    "mock_robinhood_quote",
    "mock_robinhood_api_error",
    "mock_schwab_quote",
    "mock_schwab_auth_error",
]


@pytest.mark.unit
@pytest.mark.journey_system
def test_required_response_fixture_files_exist_and_parse() -> None:
    """Ensure all required fixture files exist and are valid JSON."""
    for rel_path in REQUIRED_FIXTURE_PATHS:
        path = FIXTURE_ROOT / rel_path
        assert path.exists(), f"Missing fixture file: {path}"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict | list), f"Unexpected JSON type in {path}"


@pytest.mark.unit
@pytest.mark.journey_system
@pytest.mark.parametrize("fixture_name", REQUIRED_FIXTURE_NAMES)
def test_required_fixture_names_are_exposed(
    fixture_name: str, request: pytest.FixtureRequest
) -> None:
    """Ensure required fixture names can be requested by tests."""
    payload = request.getfixturevalue(fixture_name)
    assert isinstance(payload, dict | list)


@pytest.mark.unit
@pytest.mark.journey_system
def test_shared_fixture_returns_deep_copies(request: pytest.FixtureRequest) -> None:
    """Mutating one fixture instance should not affect subsequent retrievals."""
    first = request.getfixturevalue("mock_robinhood_quote")
    second = request.getfixturevalue("robinhood_quote_payload")

    assert isinstance(first, dict)
    assert isinstance(second, dict)

    original = second["last_trade_price"]
    first["last_trade_price"] = "999.99"
    assert second["last_trade_price"] == original


@pytest.mark.unit
@pytest.mark.journey_system
def test_schwab_auth_fixture_shape(request: pytest.FixtureRequest) -> None:
    """Schwab auth fixture should keep the structured error envelope."""
    payload: Any = request.getfixturevalue("mock_schwab_auth_error")
    assert payload["result"]["status"] == "error"
    assert payload["result"]["error"] == "Not authenticated"
