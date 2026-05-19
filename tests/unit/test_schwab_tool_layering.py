"""Architecture tests for Schwab tool layering boundaries."""

import ast
from pathlib import Path

SCHWAB_TOOL_FILES = [
    "schwab_account_tools.py",
    "schwab_market_tools.py",
    "schwab_options_tools.py",
    "schwab_trading_tools.py",
]


def test_schwab_tools_do_not_import_auth_coordinator() -> None:
    """Schwab tools must not import broker auth coordinator directly."""
    tools_dir = Path("src/open_stocks_mcp/tools")

    for filename in SCHWAB_TOOL_FILES:
        path = tools_dir / filename
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == (
                "open_stocks_mcp.brokers.auth_coordinator"
            ):
                raise AssertionError(
                    f"{filename} imports from brokers.auth_coordinator"
                )
