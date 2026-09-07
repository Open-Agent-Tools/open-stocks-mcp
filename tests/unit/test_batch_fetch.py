"""Unit tests for the batch_fetch helpers and the N+1 regressions they cover.

Covers:
- ``gather_bounded`` honours the concurrency cap and surfaces exceptions
  in place rather than aborting the batch.
- ``dedupe_preserving_order`` removes duplicates and skips falsy keys.
- The 6 enrichment call sites flagged in issue #986 only issue ONE broker
  lookup per distinct key, even when the same URL/option ID appears across
  many rows, and they handle large input lists without leaking serial
  awaits.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.batch_fetch import (
    DEFAULT_BATCH_CONCURRENCY,
    dedupe_preserving_order,
    gather_bounded,
)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_gather_bounded_empty() -> None:
    assert await gather_bounded([]) == []


@pytest.mark.asyncio
@pytest.mark.unit
async def test_gather_bounded_preserves_order_and_returns_exceptions() -> None:
    async def ok(value: int) -> int:
        await asyncio.sleep(0)
        return value

    async def boom() -> int:
        raise RuntimeError("nope")

    results = await gather_bounded([ok(1), boom(), ok(3)])

    assert results[0] == 1
    assert isinstance(results[1], RuntimeError)
    assert results[2] == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_gather_bounded_caps_concurrent_tasks() -> None:
    """At most `limit` coroutines should be in flight at any one time."""
    in_flight = 0
    peak = 0
    lock = asyncio.Lock()

    async def tracked() -> int:
        nonlocal in_flight, peak
        async with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        await asyncio.sleep(0.005)
        async with lock:
            in_flight -= 1
        return 1

    await gather_bounded([tracked() for _ in range(50)], limit=4)
    assert peak <= 4


@pytest.mark.unit
def test_dedupe_preserving_order_strips_falsy_and_dedupes() -> None:
    assert dedupe_preserving_order(["a", None, "b", "", "a", "c", "b", None]) == [
        "a",
        "b",
        "c",
    ]


@pytest.mark.unit
def test_dedupe_preserving_order_empty() -> None:
    assert dedupe_preserving_order([]) == []
    assert dedupe_preserving_order([None, "", None]) == []


@pytest.mark.unit
def test_default_concurrency_is_sane() -> None:
    assert 1 < DEFAULT_BATCH_CONCURRENCY <= 32


# ---------------------------------------------------------------------------
# Regression tests for the 6 N+1 sites flagged in issue #986
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.journey_portfolio
async def test_get_positions_dedupes_repeated_instrument_urls() -> None:
    """Duplicate instrument URLs across positions hit the broker once each."""
    from open_stocks_mcp.tools.robinhood_account_tools import get_positions

    aapl = "https://robinhood.com/instruments/aapl123/"
    googl = "https://robinhood.com/instruments/googl456/"
    positions_payload = [
        {
            "instrument": aapl,
            "quantity": "10.0000",
            "average_buy_price": "150.00",
            "updated_at": "t",
        },
        {
            "instrument": aapl,  # duplicate — same instrument as the first row
            "quantity": "1.0000",
            "average_buy_price": "151.00",
            "updated_at": "t",
        },
        {
            "instrument": googl,
            "quantity": "5.0000",
            "average_buy_price": "2500.00",
            "updated_at": "t",
        },
    ]

    with (
        patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.get_open_stock_positions",
            return_value=positions_payload,
        ),
        patch(
            "open_stocks_mcp.tools.robinhood_account_tools.rh.get_symbol_by_url",
            side_effect=lambda url: {aapl: "AAPL", googl: "GOOGL"}[url],
        ) as mock_symbol,
    ):
        result = await get_positions()

    # Two unique URLs => exactly two lookups, regardless of position count.
    assert mock_symbol.call_count == 2
    assert sorted(call.args[0] for call in mock_symbol.call_args_list) == sorted(
        [aapl, googl]
    )
    symbols = [p["symbol"] for p in result["result"]["positions"]]
    assert symbols == ["AAPL", "AAPL", "GOOGL"]


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.journey_portfolio
async def test_get_positions_handles_large_list_with_bounded_concurrency() -> None:
    """A 50-position payload completes and stays within the concurrency cap."""
    from open_stocks_mcp.tools.robinhood_account_tools import get_positions

    n = 50
    positions_payload = [
        {
            "instrument": f"https://robinhood.com/instruments/sym{i}/",
            "quantity": "1.0000",
            "average_buy_price": "10.00",
            "updated_at": "t",
        }
        for i in range(n)
    ]

    in_flight = 0
    peak = 0
    lock = asyncio.Lock()

    from open_stocks_mcp.tools import robinhood_account_tools as mod

    async def fake_symbol_lookup(url: str) -> str:
        nonlocal in_flight, peak
        async with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        # Yield twice so concurrent tasks have a chance to ramp up to the cap.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        async with lock:
            in_flight -= 1
        return url.rstrip("/").rsplit("/", 1)[-1].upper()

    async def fake_execute_with_retry(func: Any, *args: Any, **kwargs: Any) -> Any:
        if func is mod.rh.get_open_stock_positions:
            return positions_payload
        if func is mod.rh.get_symbol_by_url:
            return await fake_symbol_lookup(args[0])
        raise AssertionError(f"unexpected fn: {func}")

    with patch.object(
        mod, "execute_with_retry", new=AsyncMock(side_effect=fake_execute_with_retry)
    ):
        result = await get_positions()

    assert result["result"]["count"] == n
    assert peak <= DEFAULT_BATCH_CONCURRENCY
    assert {p["symbol"] for p in result["result"]["positions"]} == {
        f"SYM{i}" for i in range(n)
    }


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.journey_research
async def test_get_dividends_dedupes_repeated_instrument_urls() -> None:
    """get_dividends: same instrument URL across rows hits broker once."""
    from open_stocks_mcp.tools import robinhood_dividend_tools as mod

    aapl_url = "https://robinhood.com/instruments/aapl/"
    dividends_payload = [
        {"instrument": aapl_url, "amount": "1.00", "state": "paid"},
        {"instrument": aapl_url, "amount": "1.00", "state": "paid"},
        {"instrument": aapl_url, "amount": "1.00", "state": "paid"},
    ]

    call_count = 0

    async def fake_execute(func: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        if func is mod.rh.account.get_dividends:
            return dividends_payload
        if func is mod.rh.stocks.get_instrument_by_url:
            call_count += 1
            return {"symbol": "AAPL", "simple_name": "Apple"}
        raise AssertionError(f"unexpected fn: {func}")

    session = MagicMock()
    session.ensure_authenticated = AsyncMock(return_value=True)
    with (
        patch.object(
            mod, "execute_with_retry", new=AsyncMock(side_effect=fake_execute)
        ),
        patch.object(mod, "get_session_manager", return_value=session),
    ):
        result = await mod.get_dividends()

    # 3 dividends sharing one URL → exactly ONE instrument lookup.
    assert call_count == 1
    assert all(d["symbol"] == "AAPL" for d in result["result"]["dividends"])


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.journey_research
async def test_get_stock_loan_payments_dedupes_repeated_instrument_urls() -> None:
    """get_stock_loan_payments: shared instrument URL → one broker lookup."""
    from open_stocks_mcp.tools import robinhood_dividend_tools as mod

    amc_url = "https://robinhood.com/instruments/amc/"
    payments_payload = [
        {"instrument": amc_url, "amount": "0.10", "state": "paid"},
        {"instrument": amc_url, "amount": "0.20", "state": "paid"},
    ]

    call_count = 0

    async def fake_execute(func: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        if func is mod.rh.account.get_stock_loan_payments:
            return payments_payload
        if func is mod.rh.stocks.get_instrument_by_url:
            call_count += 1
            return {"symbol": "AMC", "simple_name": "AMC Entertainment"}
        raise AssertionError(f"unexpected fn: {func}")

    session = MagicMock()
    session.ensure_authenticated = AsyncMock(return_value=True)
    with (
        patch.object(
            mod, "execute_with_retry", new=AsyncMock(side_effect=fake_execute)
        ),
        patch.object(mod, "get_session_manager", return_value=session),
    ):
        result = await mod.get_stock_loan_payments()

    assert call_count == 1
    assert all(p["symbol"] == "AMC" for p in result["result"]["loan_payments"])


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.journey_options
async def test_get_open_option_positions_with_details_dedupes_option_ids() -> None:
    """Option positions sharing the same option_id only fetch instrument once."""
    from open_stocks_mcp.tools.options.positions import (
        get_open_option_positions_with_details,
    )

    positions_payload = [
        {
            "id": "p1",
            "chain_symbol": "AAPL",
            "option_id": "opt-1",
            "total_equity": "10.00",
            "unrealized_pnl": "1.00",
        },
        {
            "id": "p2",
            "chain_symbol": "AAPL",
            "option_id": "opt-1",  # duplicate option_id (e.g. multi-leg)
            "total_equity": "10.00",
            "unrealized_pnl": "1.00",
        },
        {
            "id": "p3",
            "chain_symbol": "MSFT",
            "option_id": "opt-2",
            "total_equity": "10.00",
            "unrealized_pnl": "1.00",
        },
    ]

    instrument_payloads = {
        "opt-1": {
            "type": "call",
            "strike_price": "150.0000",
            "occ_symbol": "AAPL_C",
            "tradability": "tradable",
            "state": "active",
            "chain_symbol": "AAPL",
            "expiration_date": "2025-01-17",
            "rhs_tradability": "tradable",
        },
        "opt-2": {
            "type": "put",
            "strike_price": "300.0000",
            "occ_symbol": "MSFT_P",
            "tradability": "tradable",
            "state": "active",
            "chain_symbol": "MSFT",
            "expiration_date": "2025-01-17",
            "rhs_tradability": "tradable",
        },
    }

    with (
        patch(
            "open_stocks_mcp.tools.options.positions.rh.options.get_open_option_positions",
            return_value=positions_payload,
        ),
        patch(
            "open_stocks_mcp.tools.options.positions.rh.options.get_option_instrument_data_by_id",
            side_effect=lambda option_id: instrument_payloads[option_id],
        ) as mock_instrument,
    ):
        result = await get_open_option_positions_with_details()

    # 3 positions, 2 unique option ids → exactly 2 instrument lookups.
    assert mock_instrument.call_count == 2
    types = [p["option_type"] for p in result["result"]["positions"]]
    assert types == ["call", "call", "put"]
    assert result["result"]["enrichment_success_rate"] == "100%"


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.journey_trading
async def test_get_all_open_stock_orders_dedupes_repeated_instrument_urls() -> None:
    """Many open orders sharing one instrument URL → one symbol lookup."""
    from open_stocks_mcp.tools import robinhood_trading_tools as mod

    aapl_url = "https://robinhood.com/instruments/aapl/"
    orders_payload = [
        {
            "id": f"o{i}",
            "instrument": aapl_url,
            "side": "buy",
            "state": "queued",
        }
        for i in range(5)
    ]

    call_count = 0

    async def fake_execute(func: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        if func is mod.rh.get_all_open_stock_orders:
            return orders_payload
        if func is mod.rh.get_symbol_by_url:
            call_count += 1
            return "AAPL"
        raise AssertionError(f"unexpected fn: {func}")

    with patch.object(
        mod, "execute_with_retry", new=AsyncMock(side_effect=fake_execute)
    ):
        result = await mod.get_all_open_stock_orders()

    assert call_count == 1
    assert result["result"]["count"] == 5
    assert all(o["symbol"] == "AAPL" for o in result["result"]["orders"])


@pytest.mark.asyncio
@pytest.mark.unit
async def test_broker_comparison_fans_out_robinhood_quotes_concurrently() -> None:
    """The Robinhood comparison collector should not await quotes serially."""
    from open_stocks_mcp.tools import broker_comparison_tools as mod

    symbols = ["AAPL", "MSFT", "GOOGL"]

    in_flight = 0
    peak = 0
    lock = asyncio.Lock()

    async def fake_get_stock_price(symbol: str) -> dict[str, Any]:
        nonlocal in_flight, peak
        async with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        async with lock:
            in_flight -= 1
        return {"result": {"price": 100.0, "change": 1.0, "change_percent": 0.5}}

    with (
        patch.object(
            mod, "get_stock_price", new=AsyncMock(side_effect=fake_get_stock_price)
        ),
        patch.object(
            mod,
            "get_portfolio",
            new=AsyncMock(return_value={"result": {"equity": 0, "buying_power": 0}}),
        ),
        patch.object(
            mod,
            "get_positions",
            new=AsyncMock(return_value={"result": {"positions": []}}),
        ),
        patch.object(
            mod,
            "get_stock_orders",
            new=AsyncMock(return_value={"result": {"orders": []}}),
        ),
    ):
        data = await mod._collect_robinhood_comparison(
            symbols=symbols, include_orders=False, max_orders=5
        )

    # All three symbols ran with overlapping in-flight tasks (>1 peak),
    # proving the gather is concurrent rather than serial.
    assert peak >= 2
    assert set(data["pricing"].keys()) == set(symbols)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_broker_comparison_fans_out_schwab_quotes_concurrently() -> None:
    """The Schwab comparison collector should not await quotes serially."""
    from open_stocks_mcp.tools import broker_comparison_tools as mod

    symbols = ["AAPL", "MSFT", "GOOGL"]

    in_flight = 0
    peak = 0
    lock = asyncio.Lock()

    async def fake_get_schwab_quote(symbol: str) -> dict[str, Any]:
        nonlocal in_flight, peak
        async with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        async with lock:
            in_flight -= 1
        return {"result": {"last_price": 100.0, "change": 1.0, "change_percent": 0.5}}

    with (
        patch.object(
            mod,
            "get_schwab_account_numbers",
            new=AsyncMock(return_value={"result": {"accounts": [{"hash_value": "h"}]}}),
        ),
        patch.object(
            mod, "get_schwab_quote", new=AsyncMock(side_effect=fake_get_schwab_quote)
        ),
        patch.object(
            mod,
            "get_schwab_account_balances",
            new=AsyncMock(return_value={"result": {"current_balances": {}}}),
        ),
        patch.object(
            mod,
            "get_schwab_portfolio",
            new=AsyncMock(return_value={"result": {"positions": []}}),
        ),
        patch.object(
            mod,
            "get_schwab_orders",
            new=AsyncMock(return_value={"result": {"orders": []}}),
        ),
    ):
        data = await mod._collect_schwab_comparison(
            symbols=symbols, include_orders=False, max_orders=5
        )

    assert peak >= 2
    assert set(data["pricing"].keys()) == set(symbols)
