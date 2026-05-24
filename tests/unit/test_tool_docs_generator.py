import pytest

from open_stocks_mcp.server.app import mcp
from open_stocks_mcp.server.tool_docs import (
    build_tool_docs_payload,
    render_tool_docs_markdown,
)


@pytest.mark.unit
@pytest.mark.journey_system
@pytest.mark.anyio
async def test_build_tool_docs_payload_matches_live_registry() -> None:
    payload = await build_tool_docs_payload(mcp)
    tools = await mcp.list_tools()

    assert payload["result"]["count"] == len(tools)
    assert payload["result"]["tools"]
    for item in payload["result"]["tools"]:
        assert "name" in item
        assert "description" in item


@pytest.mark.unit
@pytest.mark.journey_system
@pytest.mark.anyio
async def test_markdown_contains_count_and_headings_for_all_tools() -> None:
    payload = await build_tool_docs_payload(mcp)
    markdown = render_tool_docs_markdown(payload)

    assert markdown.startswith("# Open Stocks MCP — Tool Reference")
    assert f"Total tools: {payload['result']['count']}" in markdown
    for tool in payload["result"]["tools"]:
        assert f"## {tool['name']}" in markdown
