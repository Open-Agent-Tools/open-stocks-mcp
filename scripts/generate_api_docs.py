"""Generate API documentation from registered MCP tools."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

HEADER = "# Open Stocks MCP — Tool Reference\n"


async def build_doc(mcp: Any) -> str:
    """Build deterministic markdown from registered tools."""
    tools = await mcp.list_tools()
    tool_entries = sorted(tools, key=lambda tool: tool.name)

    lines = [HEADER, f"{len(tool_entries)} tools registered\n"]
    for tool in tool_entries:
        description = tool.description or "No description provided."
        lines.extend([f"### {tool.name}\n", f"{description}\n"])

    return "\n".join(lines).rstrip() + "\n"


def main(output_path: Path | None = None) -> Path:
    """Render docs/api/tools.md (or custom output path)."""
    from open_stocks_mcp.server.app import mcp

    target = output_path or Path("docs/api/tools.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    markdown = asyncio.run(build_doc(mcp))
    target.write_text(markdown, encoding="utf-8")
    return target


if __name__ == "__main__":
    path = main()
    print(f"Generated {path}")
