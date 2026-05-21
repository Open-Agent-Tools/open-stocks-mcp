"""Generate Markdown reference for all registered MCP tools."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from open_stocks_mcp.server.app import mcp
from open_stocks_mcp.server.tool_docs import (
    build_tool_docs_payload,
    render_tool_docs_markdown,
)


async def _generate(output: Path) -> Path:
    payload = await build_tool_docs_payload(mcp)
    content = render_tool_docs_markdown(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/MCP_TOOLS_REFERENCE.md"),
    )
    args = parser.parse_args()
    written = asyncio.run(_generate(args.output))
    print(f"Generated {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
