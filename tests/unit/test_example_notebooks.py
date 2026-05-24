from pathlib import Path

import nbformat
import pytest

from open_stocks_mcp.server.app import mcp

PORTFOLIO_NOTEBOOK = Path("examples/notebooks/portfolio_snapshot.ipynb")
OPTIONS_NOTEBOOK = Path("examples/notebooks/options_analysis.ipynb")


def _source_text(cell: nbformat.NotebookNode) -> str:
    source = cell.get("source", "")
    if isinstance(source, str):
        return source
    return "".join(source)


@pytest.mark.unit
@pytest.mark.journey_system
@pytest.mark.anyio
async def test_example_notebooks_have_required_structure() -> None:
    live_tool_names = {tool.name for tool in await mcp.list_tools()}

    for notebook_path in (PORTFOLIO_NOTEBOOK, OPTIONS_NOTEBOOK):
        notebook = nbformat.read(notebook_path, as_version=4)
        markdown_cells = [
            _source_text(cell)
            for cell in notebook.cells
            if cell.get("cell_type") == "markdown"
        ]
        code_cells = [
            _source_text(cell)
            for cell in notebook.cells
            if cell.get("cell_type") == "code"
        ]

        assert any(
            "ROBINHOOD_USERNAME" in cell and "ROBINHOOD_PASSWORD" in cell
            for cell in markdown_cells
        )
        assert len(code_cells) >= 3
        assert any(
            any(tool_name in cell for tool_name in live_tool_names)
            for cell in code_cells
        )
        assert all("your_password" not in cell for cell in markdown_cells + code_cells)
