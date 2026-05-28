"""Regression test: every registered schwab_* MCP tool must have an ADK eval fixture
or appear in the explicit omission list with justification.

Run with: pytest tests/unit/test_schwab_eval_coverage.py -v
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

EVAL_DIR = Path(__file__).parent.parent / "evals"

# Tools excluded from eval coverage with documented justification.
# Streaming tools: real-time WebSocket subscriptions don't fit the ADK
#   request/response eval model — there is no stable final_response to assert.
# Trading mutation tools: require live credentials AND execute real market orders
#   or destructive cancellations; covered by integration journey tests instead.
EVAL_OMISSION_ALLOWLIST: frozenset[str] = frozenset(
    [
        # --- Streaming (real-time subscriptions, no request/response eval model) ---
        "schwab_stream_account_activity",
        "schwab_stream_level2",
        "schwab_stream_option_quotes",
        "schwab_stream_quotes",
        # --- Trading mutations (execute real orders or destructive cancellations) ---
        "schwab_buy_stock_market",
        "schwab_sell_stock_market",
        "schwab_buy_stock_limit",
        "schwab_sell_stock_limit",
        "schwab_place_order",
        "schwab_cancel_order",
        "schwab_cancel_all_stock_orders",
        "schwab_cancel_all_option_orders",
        "schwab_cancel_option_order",
        "schwab_replace_order",
        "schwab_order_sell_stop",
        "schwab_order_buy_option_limit",
        "schwab_order_sell_option_limit",
        "schwab_order_option_credit_spread",
        "schwab_order_option_debit_spread",
        "schwab_option_buy_to_open",
        "schwab_option_sell_to_close",
    ]
)


def _collect_eval_tool_names() -> set[str]:
    """Return all MCP tool names referenced inside tests/evals/*schwab*_test.json."""
    covered: set[str] = set()
    for path in EVAL_DIR.glob("*schwab*_test.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for case in data.get("eval_cases", []):
            for turn in case.get("conversation", []):
                for tool_use in turn.get("intermediate_data", {}).get("tool_uses", []):
                    covered.add(tool_use["name"])
    return covered


def _collect_registered_schwab_tools() -> list[str]:
    """Return all MCP tool names that start with 'schwab_' from the live server."""
    from open_stocks_mcp.server.app import mcp

    tools = asyncio.run(mcp.list_tools())
    return sorted(t.name for t in tools if t.name.startswith("schwab_"))


@pytest.mark.unit
@pytest.mark.journey_system
def test_every_schwab_tool_has_eval_or_omission_justification() -> None:
    """Fail if a registered schwab_* tool has no eval fixture and no omission entry.

    This test acts as a coverage gate: adding a new Schwab tool to the server
    requires either adding a corresponding eval fixture in tests/evals/ or
    adding the tool name to EVAL_OMISSION_ALLOWLIST with a comment explaining why.
    """
    eval_covered = _collect_eval_tool_names()
    registered = _collect_registered_schwab_tools()

    uncovered = [
        name
        for name in registered
        if name not in eval_covered and name not in EVAL_OMISSION_ALLOWLIST
    ]

    assert uncovered == [], (
        "The following registered schwab_* tools have no ADK eval fixture and are "
        "not in EVAL_OMISSION_ALLOWLIST:\n"
        + "\n".join(f"  - {name}" for name in uncovered)
        + "\n\nFix by adding tests/evals/*schwab*_test.json fixtures that exercise "
        "these tools, or add them to EVAL_OMISSION_ALLOWLIST in this file with a "
        "comment justifying the omission."
    )


@pytest.mark.unit
@pytest.mark.journey_system
def test_omission_allowlist_has_no_phantom_entries() -> None:
    """Warn if an omission allowlist entry no longer corresponds to a registered tool.

    Phantom entries indicate a tool was renamed or removed without updating the list.
    """
    registered = set(_collect_registered_schwab_tools())
    phantoms = [name for name in EVAL_OMISSION_ALLOWLIST if name not in registered]

    assert phantoms == [], (
        "EVAL_OMISSION_ALLOWLIST contains entries that are no longer registered "
        "schwab_* MCP tools:\n"
        + "\n".join(f"  - {name}" for name in sorted(phantoms))
        + "\n\nRemove stale entries from EVAL_OMISSION_ALLOWLIST in "
        "tests/unit/test_schwab_eval_coverage.py."
    )
