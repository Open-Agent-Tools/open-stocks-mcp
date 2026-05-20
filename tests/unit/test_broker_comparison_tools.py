"""Tests for broker comparison tools."""

from unittest.mock import patch

import pytest

from open_stocks_mcp.tools.broker_comparison_tools import get_broker_comparison


@pytest.mark.asyncio
async def test_broker_comparison_normalizes_data() -> None:
    """Comparison should normalize robinhood and schwab data for side-by-side output."""
    with (
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_portfolio",
            return_value={
                "result": {
                    "equity": "1000.5",
                    "buying_power": "250.25",
                    "market_value": "1000.5",
                    "status": "success",
                }
            },
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_positions",
            return_value={
                "result": {
                    "positions": [
                        {
                            "symbol": "AAPL",
                            "quantity": "2",
                            "average_buy_price": "150",
                        }
                    ],
                    "status": "success",
                }
            },
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_stock_orders",
            return_value={
                "result": {
                    "orders": [
                        {
                            "symbol": "AAPL",
                            "side": "BUY",
                            "quantity": "1",
                            "average_price": "151",
                            "state": "filled",
                        }
                    ],
                    "status": "success",
                }
            },
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_stock_price",
            return_value={
                "result": {
                    "symbol": "AAPL",
                    "price": 175.11,
                    "status": "success",
                }
            },
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_schwab_account_numbers",
            return_value={
                "result": {
                    "accounts": [{"account_id": "1", "hash_value": "hash-1"}],
                    "status": "success",
                }
            },
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_schwab_account_balances",
            return_value={
                "result": {
                    "current_balances": {
                        "market_value": 2000.0,
                        "buying_power": 600.0,
                    },
                    "status": "success",
                }
            },
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_schwab_portfolio",
            return_value={
                "result": {
                    "positions": [
                        {
                            "symbol": "AAPL",
                            "quantity": 3,
                            "average_price": 140,
                            "market_value": 525,
                        }
                    ],
                    "status": "success",
                }
            },
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_schwab_orders",
            return_value={
                "result": {
                    "orders": [
                        {
                            "orderLegCollection": [
                                {
                                    "instruction": "SELL",
                                    "instrument": {"symbol": "AAPL"},
                                    "quantity": 1,
                                }
                            ],
                            "status": "FILLED",
                            "price": 170.0,
                        }
                    ],
                    "status": "success",
                }
            },
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_schwab_quote",
            return_value={
                "result": {
                    "symbol": "AAPL",
                    "last_price": 174.98,
                    "status": "success",
                }
            },
        ),
    ):
        result = await get_broker_comparison(["AAPL"], include_orders=True, max_orders=5)

    payload = result["result"]
    assert payload["status"] == "success"
    assert payload["brokers"]["robinhood"]["source"] == "robinhood"
    assert payload["brokers"]["schwab"]["source"] == "schwab"
    assert payload["brokers"]["robinhood"]["confidence"] in {"high", "medium"}
    assert payload["brokers"]["schwab"]["confidence"] in {"high", "medium"}
    assert payload["comparison"]["AAPL"]["robinhood"]["price"] == 175.11
    assert payload["comparison"]["AAPL"]["schwab"]["price"] == 174.98
    assert payload["availability_notes"] == []


@pytest.mark.asyncio
async def test_broker_comparison_returns_partial_on_schwab_failure() -> None:
    """One broker failure should not collapse successful broker comparison output."""
    with (
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_portfolio",
            return_value={"result": {"equity": "100", "status": "success"}},
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_positions",
            return_value={"result": {"positions": [{"symbol": "AAPL", "quantity": "1"}], "status": "success"}},
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_stock_orders",
            return_value={"result": {"orders": [], "status": "success"}},
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_stock_price",
            return_value={"result": {"symbol": "AAPL", "price": 175.0, "status": "success"}},
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_schwab_account_numbers",
            return_value={"result": {"status": "broker_unavailable", "error": "offline"}},
        ),
    ):
        result = await get_broker_comparison(["AAPL"], include_orders=False)

    payload = result["result"]
    assert payload["status"] == "partial"
    assert payload["brokers"]["robinhood"]["available"] is True
    assert payload["brokers"]["schwab"]["available"] is False
    assert payload["comparison"]["AAPL"]["robinhood"]["price"] == 175.0
    assert any("schwab" in note.lower() for note in payload["availability_notes"])
