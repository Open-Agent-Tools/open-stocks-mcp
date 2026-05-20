import json
from pathlib import Path

import pytest

NOTEBOOK_01 = Path("examples/notebooks/01_market_data_quickstart.ipynb")
NOTEBOOK_02 = Path("examples/notebooks/02_trading_safe_dry_run.ipynb")


def _source_text(cell: dict) -> str:
    source = cell.get("source", "")
    if isinstance(source, str):
        return source
    return "".join(source)


def _code_sources(notebook: dict) -> list[str]:
    return [
        _source_text(cell)
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    ]


@pytest.mark.unit
@pytest.mark.journey_system
def test_market_data_notebook_is_valid():
    notebook = json.loads(NOTEBOOK_01.read_text(encoding="utf-8"))

    assert notebook.get("nbformat", 0) >= 4
    first_cell = notebook["cells"][0]
    assert first_cell["cell_type"] == "markdown"
    first_source = _source_text(first_cell)
    assert "Prerequisites & Safety" in first_source
    assert "ROBINHOOD_USERNAME" in first_source

    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    code_sources = [_source_text(cell) for cell in code_cells]

    assert any("MCP_HTTP_URL" in src and "http://localhost:3001/mcp" in src for src in code_sources)
    for cell in code_cells:
        assert cell.get("outputs") == []
        assert cell.get("execution_count") is None

    assert any(
        token in src for src in code_sources for token in ["account_info", "portfolio", "stock_price"]
    )


@pytest.mark.unit
@pytest.mark.journey_system
def test_trading_dry_run_notebook_is_safe():
    notebook = json.loads(NOTEBOOK_02.read_text(encoding="utf-8"))

    assert notebook.get("nbformat", 0) >= 4
    first_cell = notebook["cells"][0]
    assert first_cell["cell_type"] == "markdown"
    first_source = _source_text(first_cell)
    assert "SAFETY" in first_source
    assert "dry run" in first_source.lower()

    code_sources = _code_sources(notebook)
    assert any("MCP_HTTP_URL" in source for source in code_sources)
    assert any("http://localhost:3001/mcp" in source for source in code_sources)
    assert any("list_tools()" in source for source in code_sources)
    assert any("trading_tools" in source for source in code_sources)
    assert any(
        '"timeInForce": "gfd"' in source and "print(" in source
        for source in code_sources
    )

    forbidden = [
        "rh.order_buy_market",
        "rh.order_sell_market",
        "rh.order_buy_limit",
        "rh.order_sell_limit",
        "order_buy_option_limit",
    ]
    for source in code_sources:
        for token in forbidden:
            assert token not in source


@pytest.mark.unit
@pytest.mark.journey_system
def test_api_docs_readme_links_from_root_readme():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "[API docs and notebook guide](docs/api/README.md)" in readme
    assert "docs/api/tools.md" in readme

    api_docs = Path("docs/api/README.md").read_text(encoding="utf-8")
    assert "uv run python scripts/generate_api_docs.py" in api_docs
    assert "uv run jupyter lab examples/notebooks/" in api_docs
    for env_var in [
        "ROBINHOOD_USERNAME",
        "ROBINHOOD_PASSWORD",
        "SCHWAB_API_KEY",
        "SCHWAB_APP_SECRET",
        "SCHWAB_CALLBACK_URL",
        "SCHWAB_TOKEN_PATH",
    ]:
        assert env_var in api_docs
    assert "running trading cells places real orders" in api_docs.lower()
    assert "not run in CI" in api_docs
