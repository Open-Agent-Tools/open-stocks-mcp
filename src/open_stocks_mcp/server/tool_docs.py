"""Helpers for generating MCP tool documentation payloads."""

from __future__ import annotations

from typing import Any

DOCS_HEADER = "# Open Stocks MCP — Tool Reference"


def _serialize_tools(tools: list[Any]) -> dict[str, Any]:
    serialized_tools: list[dict[str, Any]] = []
    for tool in sorted(tools, key=lambda item: item.name):
        input_schema = getattr(tool, "inputSchema", {})
        if hasattr(input_schema, "model_dump"):
            input_schema = input_schema.model_dump()
        serialized_tools.append(
            {
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": input_schema or {},
            }
        )
    return {"result": {"tools": serialized_tools, "count": len(serialized_tools)}}


async def build_tool_docs_payload(mcp: Any) -> dict[str, Any]:
    """Build a structured payload from the live MCP registry."""
    tools = await mcp.list_tools()
    return _serialize_tools(tools)


def build_tool_docs_payload_from_snapshot(mcp: Any) -> dict[str, Any]:
    """Build a docs payload from the tool manager without awaiting list_tools()."""
    tool_manager = getattr(mcp, "_tool_manager", None)
    tools_map = getattr(tool_manager, "_tools", {}) if tool_manager else {}
    return _serialize_tools(list(tools_map.values()))


def render_tool_docs_markdown(payload: dict[str, Any]) -> str:
    """Render deterministic markdown from tool payload data."""
    result = payload["result"]
    tools = result["tools"]
    count = result["count"]

    lines = [DOCS_HEADER, "", f"Total tools: {count}", ""]
    for tool in tools:
        description = tool["description"] or "No description provided."
        lines.extend([f"## {tool['name']}", "", description, ""])

    return "\n".join(lines).rstrip() + "\n"


def build_tool_openapi_paths(payload: dict[str, Any]) -> dict[str, Any]:
    """Build synthetic OpenAPI path docs for MCP JSON-RPC tool calls."""
    paths: dict[str, Any] = {}
    for tool in payload["result"]["tools"]:
        path = f"/mcp/tools/{tool['name']}"
        paths[path] = {
            "post": {
                "summary": f"MCP tool: {tool['name']}",
                "description": (
                    "Documentation-only endpoint. Call this tool via `POST /mcp` "
                    "using JSON-RPC method `tools/call`."
                ),
                "operationId": f"mcp_tool_{tool['name']}",
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {"schema": tool.get("inputSchema", {})}
                    },
                },
                "responses": {
                    "200": {
                        "description": (
                            "Tool result payload returned by MCP JSON-RPC `tools/call`."
                        )
                    }
                },
            }
        }
    return paths
