import re
from pathlib import Path

import nbformat
import pytest

from open_stocks_mcp.server.app import mcp

pytestmark = [pytest.mark.unit, pytest.mark.journey_system]

_REPO_ROOT = Path(__file__).parents[2]
NOTEBOOK_DIR = _REPO_ROOT / "examples" / "notebooks"
PORTFOLIO_NOTEBOOK = NOTEBOOK_DIR / "portfolio_snapshot.ipynb"
OPTIONS_NOTEBOOK = NOTEBOOK_DIR / "options_analysis.ipynb"
QUICKSTART_NOTEBOOK = NOTEBOOK_DIR / "01_market_data_quickstart.ipynb"
DRY_RUN_NOTEBOOK = NOTEBOOK_DIR / "02_trading_safe_dry_run.ipynb"


async def get_registered_tool_names() -> set[str]:
    tools = await mcp.list_tools()
    return {tool.name for tool in tools}


@pytest.mark.asyncio
@pytest.mark.parametrize("notebook_path", [PORTFOLIO_NOTEBOOK, OPTIONS_NOTEBOOK])
async def test_notebook_structure(notebook_path: Path) -> None:
    assert notebook_path.exists(), f"Notebook {notebook_path} does not exist"

    # 1. Parses as nbformat v4
    try:
        nb = nbformat.read(notebook_path, as_version=4)
    except Exception as e:
        pytest.fail(f"Failed to parse {notebook_path} as nbformat v4: {e}")

    markdown_cells = [cell for cell in nb.cells if cell.cell_type == "markdown"]
    code_cells = [cell for cell in nb.cells if cell.cell_type == "code"]

    # 2. Contains markdown credential guidance mentioning both ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD
    has_credentials_guidance = False
    for cell in markdown_cells:
        source = cell.source
        if "ROBINHOOD_USERNAME" in source and "ROBINHOOD_PASSWORD" in source:
            has_credentials_guidance = True
            break

    assert has_credentials_guidance, (
        f"Notebook {notebook_path} missing markdown cell with ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD"
    )

    # 3. Contains at least three code cells
    assert len(code_cells) >= 3, (
        f"Notebook {notebook_path} must contain at least three code cells"
    )

    # 4. Has at least one code cell whose source references a registered MCP tool name
    registered_tools = await get_registered_tool_names()
    has_registered_tool = False

    for cell in code_cells:
        source = cell.source
        if any(tool_name in source for tool_name in registered_tools):
            has_registered_tool = True
            break

    assert has_registered_tool, (
        f"Notebook {notebook_path} missing a code cell referencing a registered MCP tool name"
    )


@pytest.mark.asyncio
async def test_dry_run_notebook_uses_session_list_tools() -> None:
    """dry-run notebook must call session.list_tools(), not a bare list_tools()."""
    assert DRY_RUN_NOTEBOOK.exists(), f"Notebook {DRY_RUN_NOTEBOOK} does not exist"
    nb = nbformat.read(DRY_RUN_NOTEBOOK, as_version=4)  # type: ignore[no-untyped-call]
    code_sources = [cell.source for cell in nb.cells if cell.cell_type == "code"]
    assert any("session.list_tools()" in source for source in code_sources), (
        f"Notebook {DRY_RUN_NOTEBOOK} must contain a code cell with 'session.list_tools()'"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "notebook_path",
    [PORTFOLIO_NOTEBOOK, OPTIONS_NOTEBOOK, QUICKSTART_NOTEBOOK, DRY_RUN_NOTEBOOK],
)
async def test_notebook_no_bare_tool_calls(notebook_path: Path) -> None:
    """No code cell line may begin with a bare MCP tool name followed by '('."""
    assert notebook_path.exists(), f"Notebook {notebook_path} does not exist"
    nb = nbformat.read(notebook_path, as_version=4)  # type: ignore[no-untyped-call]
    live_tool_names = await get_registered_tool_names()
    code_cells = [cell for cell in nb.cells if cell.cell_type == "code"]

    for cell in code_cells:
        # Notebooks may store newlines as literal \n or as actual newlines; handle both.
        lines = re.split(r"\\n|\n", cell.source)
        for line in lines:
            stripped = line.strip()
            for name in live_tool_names:
                if re.match(rf"{re.escape(name)}\s*\(", stripped):
                    pytest.fail(
                        f"Notebook {notebook_path}: bare tool call '{name}(' in code cell. "
                        f"Use session.call_tool('{name}', ...) instead.\n"
                        f"  Line: {line!r}"
                    )
