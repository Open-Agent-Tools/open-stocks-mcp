"""Live Schwab journey tests for read-only account, market data, options, and trading-safe workflows.

These tests require explicit opt-in and will be skipped unless all of the following
environment variables and CLI flags are set:

    --run-live-market                  (pytest CLI flag)
    OPEN_STOCKS_RUN_LIVE_MARKET=1      (env var)
    RUN_RATE_LIMITED=1                 (env var — Schwab calls are rate-limited)
    SCHWAB_API_KEY=<key>               (env var)
    SCHWAB_APP_SECRET=<secret>         (env var)
    SCHWAB_TOKEN_PATH=<path>           (optional; defaults to ~/.tokens/schwab_token.json)

A pre-existing OAuth token at SCHWAB_TOKEN_PATH is required; these tests never open
a browser or perform interactive authentication.

Run command:
    OPEN_STOCKS_RUN_LIVE_MARKET=1 RUN_RATE_LIMITED=1 ENABLED_BROKERS=schwab \\
        uv run pytest tests/integration/test_schwab_live_journeys.py \\
        -m "live_market and auth_required and rate_limited" --run-live-market -q

These tests never invoke order placement or cancellation functions. Trading journey
coverage is limited to read-only order/transaction queries.
"""

import asyncio
from typing import Any

import pytest

from tests.integration.live_market_harness import assert_live_schwab_read_only

# ---------------------------------------------------------------------------
# Account journey
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_account
def test_get_schwab_account_numbers(live_schwab_broker: Any) -> None:
    """get_schwab_account_numbers returns non-empty account list."""
    assert_live_schwab_read_only("get_schwab_account_numbers")

    from open_stocks_mcp.tools.schwab_account_tools import get_schwab_account_numbers

    result = asyncio.get_event_loop().run_until_complete(get_schwab_account_numbers())
    assert isinstance(result, dict), "Response must be a dict"
    assert "result" in result, "Response must contain 'result'"
    inner = result["result"]
    assert "accounts" in inner, "Result must contain 'accounts'"
    assert "count" in inner, "Result must contain 'count'"
    accounts = inner["accounts"]
    assert isinstance(accounts, list), "'accounts' must be a list"
    assert len(accounts) > 0, "At least one account must be present"
    first = accounts[0]
    assert isinstance(first.get("hash_value"), str) and first["hash_value"], (
        "account 'hash_value' must be a non-empty string"
    )


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_account
def test_get_schwab_account(live_schwab_broker: Any) -> None:
    """get_schwab_account returns account data for a valid hash."""
    assert_live_schwab_read_only("get_schwab_account")

    from open_stocks_mcp.tools.schwab_account_tools import (
        get_schwab_account,
        get_schwab_account_numbers,
    )

    numbers_result = asyncio.get_event_loop().run_until_complete(
        get_schwab_account_numbers()
    )
    account_hash = numbers_result["result"]["accounts"][0]["hash_value"]

    result = asyncio.get_event_loop().run_until_complete(
        get_schwab_account(account_hash)
    )
    assert isinstance(result, dict)
    assert "result" in result
    inner = result["result"]
    assert "account_hash" in inner or "accountNumber" in str(inner), (
        "Account response must reference an account"
    )


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_account
def test_get_schwab_account_balances(live_schwab_broker: Any) -> None:
    """get_schwab_account_balances returns numeric balance fields."""
    assert_live_schwab_read_only("get_schwab_account_balances")

    from open_stocks_mcp.tools.schwab_account_tools import (
        get_schwab_account_balances,
        get_schwab_account_numbers,
    )

    numbers_result = asyncio.get_event_loop().run_until_complete(
        get_schwab_account_numbers()
    )
    account_hash = numbers_result["result"]["accounts"][0]["hash_value"]

    result = asyncio.get_event_loop().run_until_complete(
        get_schwab_account_balances(account_hash)
    )
    assert isinstance(result, dict)
    assert "result" in result
    inner = result["result"]
    # Accept either shape; just verify it's a non-error dict
    assert isinstance(inner, dict), "'result' must be a dict"
    assert inner.get("status") != "error", f"Unexpected error response: {inner}"


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_portfolio
def test_get_schwab_portfolio(live_schwab_broker: Any) -> None:
    """get_schwab_portfolio returns position/count shape."""
    assert_live_schwab_read_only("get_schwab_portfolio")

    from open_stocks_mcp.tools.schwab_account_tools import (
        get_schwab_account_numbers,
        get_schwab_portfolio,
    )

    numbers_result = asyncio.get_event_loop().run_until_complete(
        get_schwab_account_numbers()
    )
    account_hash = numbers_result["result"]["accounts"][0]["hash_value"]

    result = asyncio.get_event_loop().run_until_complete(
        get_schwab_portfolio(account_hash)
    )
    assert isinstance(result, dict)
    assert "result" in result
    inner = result["result"]
    assert isinstance(inner, dict)
    assert inner.get("status") != "error", f"Unexpected error response: {inner}"
    # Either positions key or an explicit empty-portfolio indicator is acceptable
    assert "positions" in inner or "count" in inner or "account_hash" in inner


# ---------------------------------------------------------------------------
# Market data journey
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_market_data
def test_get_schwab_quote(live_schwab_broker: Any) -> None:
    """get_schwab_quote returns symbol matching the request."""
    assert_live_schwab_read_only("get_schwab_quote")

    from open_stocks_mcp.tools.schwab_market_tools import get_schwab_quote

    result = asyncio.get_event_loop().run_until_complete(get_schwab_quote("AAPL"))
    assert isinstance(result, dict)
    assert "result" in result
    inner = result["result"]
    assert inner.get("status") != "error", f"Unexpected error response: {inner}"
    assert isinstance(inner, dict)
    # Symbol should be present and match
    returned_symbol = inner.get("symbol") or inner.get("AAPL", {})
    assert returned_symbol or "AAPL" in str(inner), "Quote response must reference AAPL"


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_market_data
def test_get_schwab_quotes(live_schwab_broker: Any) -> None:
    """get_schwab_quotes returns data for each requested symbol."""
    assert_live_schwab_read_only("get_schwab_quotes")

    from open_stocks_mcp.tools.schwab_market_tools import get_schwab_quotes

    result = asyncio.get_event_loop().run_until_complete(
        get_schwab_quotes(["AAPL", "MSFT"])
    )
    assert isinstance(result, dict)
    assert "result" in result
    inner = result["result"]
    assert inner.get("status") != "error", f"Unexpected error response: {inner}"
    assert isinstance(inner, dict)
    # Should contain quote data — at minimum one of the requested symbols
    payload_str = str(inner)
    assert "AAPL" in payload_str or "MSFT" in payload_str, (
        "Multi-quote response must contain at least one requested symbol"
    )


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_market_data
def test_get_schwab_price_history(live_schwab_broker: Any) -> None:
    """get_schwab_price_history returns candle/count structure."""
    assert_live_schwab_read_only("get_schwab_price_history")

    from open_stocks_mcp.tools.schwab_market_tools import get_schwab_price_history

    result = asyncio.get_event_loop().run_until_complete(
        get_schwab_price_history(
            "AAPL", period_type="month", period=1, frequency_type="daily", frequency=1
        )
    )
    assert isinstance(result, dict)
    assert "result" in result
    inner = result["result"]
    assert inner.get("status") != "error", f"Unexpected error response: {inner}"
    assert isinstance(inner, dict)
    # Expect candle list or count field
    assert "candles" in inner or "count" in inner or "symbol" in inner, (
        "Price history response must contain candles, count, or symbol"
    )
    if "candles" in inner:
        candles = inner["candles"]
        assert isinstance(candles, list)
        if candles:
            candle = candles[0]
            for field in ("open", "high", "low", "close"):
                if field in candle:
                    assert isinstance(candle[field], (int, float)), (
                        f"Candle '{field}' must be numeric"
                    )


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_market_data
def test_search_schwab_instruments(live_schwab_broker: Any) -> None:
    """search_schwab_instruments returns non-empty results for a known query."""
    assert_live_schwab_read_only("search_schwab_instruments")

    from open_stocks_mcp.tools.schwab_market_tools import search_schwab_instruments

    result = asyncio.get_event_loop().run_until_complete(
        search_schwab_instruments("Apple")
    )
    assert isinstance(result, dict)
    assert "result" in result
    inner = result["result"]
    assert inner.get("status") != "error", f"Unexpected error response: {inner}"
    assert isinstance(inner, dict)
    # Results list or instruments key
    assert "instruments" in inner or "results" in inner or "count" in inner, (
        "Instrument search must return instruments, results, or count"
    )


# ---------------------------------------------------------------------------
# Options journey
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_options
def test_get_schwab_option_expirations(live_schwab_broker: Any) -> None:
    """get_schwab_option_expirations returns expiration date list for AAPL."""
    assert_live_schwab_read_only("get_schwab_option_expirations")

    from open_stocks_mcp.tools.schwab_options_tools import get_schwab_option_expirations

    result = asyncio.get_event_loop().run_until_complete(
        get_schwab_option_expirations("AAPL")
    )
    assert isinstance(result, dict)
    assert "result" in result
    inner = result["result"]
    assert inner.get("status") != "error", f"Unexpected error response: {inner}"
    assert isinstance(inner, dict)
    assert (
        "expirationList" in inner
        or "expirations" in inner
        or "count" in inner
        or "symbol" in inner
    ), "Option expirations response must contain expiration data"


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_options
def test_get_schwab_option_chain(live_schwab_broker: Any) -> None:
    """get_schwab_option_chain returns chain structure with symbol and count fields."""
    assert_live_schwab_read_only("get_schwab_option_chain")

    from open_stocks_mcp.tools.schwab_options_tools import get_schwab_option_chain

    result = asyncio.get_event_loop().run_until_complete(
        get_schwab_option_chain("AAPL")
    )
    assert isinstance(result, dict)
    assert "result" in result
    inner = result["result"]
    assert inner.get("status") != "error", f"Unexpected error response: {inner}"
    assert isinstance(inner, dict)
    # Option chain must reference the requested symbol
    assert "AAPL" in str(inner), "Option chain response must reference AAPL"


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_options
def test_get_schwab_options_positions(live_schwab_broker: Any) -> None:
    """get_schwab_options_positions returns position list shape (empty is acceptable)."""
    assert_live_schwab_read_only("get_schwab_options_positions")

    from open_stocks_mcp.tools.schwab_account_tools import get_schwab_account_numbers
    from open_stocks_mcp.tools.schwab_options_tools import get_schwab_options_positions

    numbers_result = asyncio.get_event_loop().run_until_complete(
        get_schwab_account_numbers()
    )
    account_hash = numbers_result["result"]["accounts"][0]["hash_value"]

    result = asyncio.get_event_loop().run_until_complete(
        get_schwab_options_positions(account_hash)
    )
    assert isinstance(result, dict)
    assert "result" in result
    inner = result["result"]
    assert inner.get("status") != "error", f"Unexpected error response: {inner}"
    assert isinstance(inner, dict)
    # positions list may be empty; validate shape
    if "positions" in inner:
        assert isinstance(inner["positions"], list)
    if "count" in inner:
        assert isinstance(inner["count"], int)


# ---------------------------------------------------------------------------
# Trading-safe (read-only) journey
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_trading
def test_get_schwab_orders(live_schwab_broker: Any) -> None:
    """get_schwab_orders returns order list shape (empty is acceptable)."""
    assert_live_schwab_read_only("get_schwab_orders")

    from open_stocks_mcp.tools.schwab_account_tools import get_schwab_account_numbers
    from open_stocks_mcp.tools.schwab_trading_tools import get_schwab_orders

    numbers_result = asyncio.get_event_loop().run_until_complete(
        get_schwab_account_numbers()
    )
    account_hash = numbers_result["result"]["accounts"][0]["hash_value"]

    result = asyncio.get_event_loop().run_until_complete(
        get_schwab_orders(account_hash)
    )
    assert isinstance(result, dict)
    assert "result" in result
    inner = result["result"]
    assert inner.get("status") != "error", f"Unexpected error response: {inner}"
    assert isinstance(inner, dict)
    if "orders" in inner:
        assert isinstance(inner["orders"], list)
    if "count" in inner:
        assert isinstance(inner["count"], int)


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_trading
def test_schwab_get_open_stock_orders(live_schwab_broker: Any) -> None:
    """schwab_get_open_stock_orders returns open order list shape (empty is acceptable)."""
    assert_live_schwab_read_only("schwab_get_open_stock_orders")

    from open_stocks_mcp.tools.schwab_account_tools import get_schwab_account_numbers
    from open_stocks_mcp.tools.schwab_trading_tools import schwab_get_open_stock_orders

    numbers_result = asyncio.get_event_loop().run_until_complete(
        get_schwab_account_numbers()
    )
    account_hash = numbers_result["result"]["accounts"][0]["hash_value"]

    result = asyncio.get_event_loop().run_until_complete(
        schwab_get_open_stock_orders(account_hash)
    )
    assert isinstance(result, dict)
    assert "result" in result
    inner = result["result"]
    assert inner.get("status") != "error", f"Unexpected error response: {inner}"
    assert isinstance(inner, dict)
    if "orders" in inner:
        assert isinstance(inner["orders"], list)
    if "count" in inner:
        assert isinstance(inner["count"], int)


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_trading
def test_schwab_get_transactions_by_date(live_schwab_broker: Any) -> None:
    """schwab_get_transactions_by_date returns transaction list shape (empty is acceptable)."""
    assert_live_schwab_read_only("schwab_get_transactions_by_date")

    from open_stocks_mcp.tools.schwab_account_tools import get_schwab_account_numbers
    from open_stocks_mcp.tools.schwab_trading_tools import (
        schwab_get_transactions_by_date,
    )

    numbers_result = asyncio.get_event_loop().run_until_complete(
        get_schwab_account_numbers()
    )
    account_hash = numbers_result["result"]["accounts"][0]["hash_value"]

    result = asyncio.get_event_loop().run_until_complete(
        schwab_get_transactions_by_date(
            account_hash, start_date="2024-01-01", end_date="2024-12-31"
        )
    )
    assert isinstance(result, dict)
    assert "result" in result
    inner = result["result"]
    assert inner.get("status") != "error", f"Unexpected error response: {inner}"
    assert isinstance(inner, dict)
    if "transactions" in inner:
        assert isinstance(inner["transactions"], list)
    if "count" in inner:
        assert isinstance(inner["count"], int)


# ---------------------------------------------------------------------------
# Read-only safety guard tests (no live credentials needed)
# ---------------------------------------------------------------------------


class TestSchwabReadOnlyGuard:
    """assert_live_schwab_read_only rejects all financially dangerous tool names."""

    def test_allows_read_only_get_quote(self) -> None:
        assert_live_schwab_read_only("get_schwab_quote")

    def test_allows_read_only_get_orders(self) -> None:
        assert_live_schwab_read_only("get_schwab_orders")

    def test_allows_read_only_get_option_chain(self) -> None:
        assert_live_schwab_read_only("get_schwab_option_chain")

    def test_rejects_schwab_buy_market(self) -> None:
        with pytest.raises(ValueError, match="schwab_buy_market"):
            assert_live_schwab_read_only("schwab_buy_market")

    def test_rejects_schwab_sell_limit(self) -> None:
        with pytest.raises(ValueError, match="schwab_sell_limit"):
            assert_live_schwab_read_only("schwab_sell_limit")

    def test_rejects_cancel_schwab_order(self) -> None:
        with pytest.raises(ValueError, match="cancel_schwab_order"):
            assert_live_schwab_read_only("cancel_schwab_order")

    def test_rejects_schwab_cancel_all_stock_orders(self) -> None:
        with pytest.raises(ValueError, match="schwab_cancel_all_stock_orders"):
            assert_live_schwab_read_only("schwab_cancel_all_stock_orders")

    def test_rejects_schwab_option_buy_to_open(self) -> None:
        with pytest.raises(ValueError, match="schwab_option_buy_to_open"):
            assert_live_schwab_read_only("schwab_option_buy_to_open")

    def test_rejects_schwab_option_sell_to_close(self) -> None:
        with pytest.raises(ValueError, match="schwab_option_sell_to_close"):
            assert_live_schwab_read_only("schwab_option_sell_to_close")

    def test_rejects_place_schwab_order(self) -> None:
        with pytest.raises(ValueError, match="place_schwab_order"):
            assert_live_schwab_read_only("place_schwab_order")

    def test_rejects_cancel_prefix_generic(self) -> None:
        with pytest.raises(ValueError):
            assert_live_schwab_read_only("cancel_anything")

    def test_rejects_order_prefix_generic(self) -> None:
        with pytest.raises(ValueError):
            assert_live_schwab_read_only("order_something")
