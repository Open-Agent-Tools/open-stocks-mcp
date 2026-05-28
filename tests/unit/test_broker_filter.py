"""Tests for broker availability filter (ENABLED_BROKERS enforcement)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from open_stocks_mcp.server.broker_filter import (
    _BROKER_AGNOSTIC_TOOLS,
    _tool_broker,
    install_broker_filter,
)

# ---------------------------------------------------------------------------
# _tool_broker mapping
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.journey_system
class TestToolBrokerMapping:
    def test_agnostic_tools_return_none(self) -> None:
        for name in _BROKER_AGNOSTIC_TOOLS:
            assert _tool_broker(name) is None, f"{name} should be agnostic"

    def test_schwab_tool_detected_by_name_prefix(self) -> None:
        assert _tool_broker("schwab_quote") == "schwab"
        assert _tool_broker("schwab_buy_stock_market") == "schwab"
        assert _tool_broker("schwab_account_numbers") == "schwab"

    def test_schwab_tool_detected_by_substring(self) -> None:
        # Any tool whose name contains "schwab" maps to schwab broker
        assert _tool_broker("get_schwab_portfolio") == "schwab"

    def test_robinhood_tool_is_default(self) -> None:
        assert _tool_broker("account_info") == "robinhood"
        assert _tool_broker("portfolio") == "robinhood"
        assert _tool_broker("stock_quote") == "robinhood"
        assert _tool_broker("positions") == "robinhood"

    def test_unknown_tool_defaults_to_robinhood(self) -> None:
        assert _tool_broker("some_new_tool") == "robinhood"


# ---------------------------------------------------------------------------
# install_broker_filter — call_tool enforcement
# ---------------------------------------------------------------------------


def _make_server(*tool_names: str) -> FastMCP:
    """Create a FastMCP instance with zero-argument stub tools."""
    server = FastMCP("test")
    for name in tool_names:

        async def _stub() -> dict[str, Any]:
            return {"result": "ok"}

        _stub.__name__ = name
        server.tool()(_stub)
    return server


def _is_blocked(result: Any) -> bool:
    """True when the broker filter returned an error CallToolResult."""
    return bool(getattr(result, "isError", False))


def _is_allowed(result: Any) -> bool:
    """True when the broker filter passed the call through to the real tool."""
    return not _is_blocked(result)


@pytest.mark.unit
@pytest.mark.journey_system
class TestInstallBrokerFilter:
    @pytest.mark.asyncio
    async def test_schwab_tool_blocked_when_robinhood_only(self) -> None:
        server = _make_server("schwab_quote", "portfolio")
        install_broker_filter(server, ["robinhood"])

        result = await server.call_tool("schwab_quote", {})
        assert _is_blocked(result)
        payload = json.loads(result.content[0].text)  # type: ignore[union-attr]
        assert payload["status"] == "error"
        assert "schwab" in payload["error"]

    @pytest.mark.asyncio
    async def test_robinhood_tool_allowed_when_robinhood_enabled(self) -> None:
        server = _make_server("portfolio")
        install_broker_filter(server, ["robinhood"])

        result = await server.call_tool("portfolio", {})
        assert _is_allowed(result)

    @pytest.mark.asyncio
    async def test_robinhood_tool_blocked_when_schwab_only(self) -> None:
        server = _make_server("portfolio")
        install_broker_filter(server, ["schwab"])

        result = await server.call_tool("portfolio", {})
        assert _is_blocked(result)
        payload = json.loads(result.content[0].text)  # type: ignore[union-attr]
        assert "robinhood" in payload["error"]

    @pytest.mark.asyncio
    async def test_schwab_tool_allowed_when_schwab_enabled(self) -> None:
        server = _make_server("schwab_quote")
        install_broker_filter(server, ["schwab"])

        result = await server.call_tool("schwab_quote", {})
        assert _is_allowed(result)

    @pytest.mark.asyncio
    async def test_all_tools_allowed_when_both_enabled(self) -> None:
        server = _make_server("schwab_quote", "portfolio")
        install_broker_filter(server, ["robinhood", "schwab"])

        assert _is_allowed(await server.call_tool("schwab_quote", {}))
        assert _is_allowed(await server.call_tool("portfolio", {}))

    @pytest.mark.asyncio
    async def test_agnostic_tools_always_allowed(self) -> None:
        server = _make_server("broker_status", "list_brokers")
        install_broker_filter(server, [])  # no brokers enabled

        assert _is_allowed(await server.call_tool("broker_status", {}))
        assert _is_allowed(await server.call_tool("list_brokers", {}))

    @pytest.mark.asyncio
    async def test_error_message_names_required_broker(self) -> None:
        server = _make_server("schwab_orders")
        install_broker_filter(server, ["robinhood"])

        result = await server.call_tool("schwab_orders", {})
        assert _is_blocked(result)
        payload = json.loads(result.content[0].text)  # type: ignore[union-attr]
        assert "schwab" in payload["error"]
        assert "ENABLED_BROKERS" in payload["error"]


# ---------------------------------------------------------------------------
# install_broker_filter — list_tools filtering
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.journey_system
class TestBrokerFilterListTools:
    @pytest.mark.asyncio
    async def test_schwab_tools_hidden_when_robinhood_only(self) -> None:
        server = _make_server("schwab_quote", "portfolio", "broker_status")
        install_broker_filter(server, ["robinhood"])

        tools = await server.list_tools()
        names = {t.name for t in tools}
        assert "schwab_quote" not in names
        assert "portfolio" in names
        assert "broker_status" in names

    @pytest.mark.asyncio
    async def test_robinhood_tools_hidden_when_schwab_only(self) -> None:
        server = _make_server("schwab_quote", "portfolio", "list_brokers")
        install_broker_filter(server, ["schwab"])

        tools = await server.list_tools()
        names = {t.name for t in tools}
        assert "portfolio" not in names
        assert "schwab_quote" in names
        assert "list_brokers" in names

    @pytest.mark.asyncio
    async def test_all_tools_visible_when_both_enabled(self) -> None:
        server = _make_server("schwab_quote", "portfolio")
        install_broker_filter(server, ["robinhood", "schwab"])

        tools = await server.list_tools()
        names = {t.name for t in tools}
        assert "schwab_quote" in names
        assert "portfolio" in names


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.journey_system
class TestBrokerFilterIdempotency:
    @pytest.mark.asyncio
    async def test_reinstall_updates_enabled_list(self) -> None:
        server = _make_server("schwab_quote")
        install_broker_filter(server, ["robinhood"])

        # Schwab blocked initially
        result = await server.call_tool("schwab_quote", {})
        assert _is_blocked(result)

        # Re-install with Schwab enabled — no double-wrapping
        install_broker_filter(server, ["robinhood", "schwab"])
        result = await server.call_tool("schwab_quote", {})
        assert _is_allowed(result)

    @pytest.mark.asyncio
    async def test_wrapper_not_stacked_on_reinstall(self) -> None:
        server = _make_server("portfolio")
        original_call = server.call_tool
        install_broker_filter(server, ["robinhood"])
        install_broker_filter(server, ["robinhood"])
        # Should still be the same single wrapper, not a double-wrapped chain
        assert server.call_tool is not original_call
        # A second install doesn't replace the wrapper
        first_wrapper = server.call_tool
        install_broker_filter(server, ["robinhood", "schwab"])
        assert server.call_tool is first_wrapper
