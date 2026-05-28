"""Compute Schwab ADK eval coverage matrix.

Usage:
    uv run python scripts/schwab_coverage.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

EVALS_DIR = Path("tests/evals")


def tools_from_eval_file(path: Path) -> set[str]:
    """Return all tool names referenced in an ADK eval JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for case in data.get("eval_cases", []):
        for conv in case.get("conversation", []):
            for use in conv.get("intermediate_data", {}).get("tool_uses", []):
                name = use.get("name", "")
                if name:
                    names.add(name)
    return names


def build_coverage(evals_dir: Path = EVALS_DIR) -> dict[str, list[str]]:
    """Map each schwab_* tool to the sorted list of eval filenames covering it.

    Only scans files matching ``*schwab*.json`` in ``evals_dir``.
    """
    tool_to_files: dict[str, list[str]] = {}
    for path in sorted(evals_dir.glob("*schwab*.json")):
        for tool in tools_from_eval_file(path):
            tool_to_files.setdefault(tool, [])
            tool_to_files[tool].append(path.name)
    for files in tool_to_files.values():
        files.sort()
    return tool_to_files


async def _get_schwab_tool_names() -> list[str]:
    from open_stocks_mcp.server.app import mcp

    tools = await mcp.list_tools()
    return sorted(t.name for t in tools if t.name.startswith("schwab_"))


def render_coverage_markdown(
    schwab_tools: list[str],
    tool_to_files: dict[str, list[str]],
) -> str:
    """Render a markdown checklist with one row per schwab_* tool."""
    lines: list[str] = []
    covered = 0
    for tool in schwab_tools:
        files = tool_to_files.get(tool, [])
        if files:
            covered += 1
            file_refs = ", ".join(f"`{f}`" for f in files)
            lines.append(f"- [x] `{tool}` — {file_refs}")
        else:
            lines.append(f"- [ ] `{tool}` — *no eval*")
    total = len(schwab_tools)
    header = f"**Coverage: {covered}/{total} schwab_* tools have ADK eval fixtures**\n\n"
    return header + "\n".join(lines) + "\n"


def main() -> None:
    tool_to_files = build_coverage()
    schwab_tools = asyncio.run(_get_schwab_tool_names())
    print(render_coverage_markdown(schwab_tools, tool_to_files), end="")


if __name__ == "__main__":
    main()
