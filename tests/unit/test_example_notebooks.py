import json
from pathlib import Path

import pytest

NOTEBOOK_01 = Path("examples/notebooks/01_market_data_quickstart.ipynb")
NOTEBOOK_02 = Path("examples/notebooks/02_trading_safe_dry_run.ipynb")


@pytest.mark.unit
@pytest.mark.journey_system
def test_market_data_notebook_is_valid():
    notebook = json.loads(NOTEBOOK_01.read_text(encoding="utf-8"))

    assert notebook.get("nbformat", 0) >= 4
    first_cell = notebook["cells"][0]
    assert first_cell["cell_type"] == "markdown"
    first_source = "".join(first_cell.get("source", []))
    assert "Prerequisites & Safety" in first_source
    assert "ROBINHOOD_USERNAME" in first_source

    code_sources = ["".join(cell.get("source", [])) for cell in notebook["cells"] if cell["cell_type"] == "code"]
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
    first_source = "".join(first_cell.get("source", []))
    assert "SAFETY" in first_source
    assert "dry run" in first_source.lower()

    forbidden = [
        "rh.order_buy_market",
        "rh.order_sell_market",
        "rh.order_buy_limit",
        "rh.order_sell_limit",
        "order_buy_option_limit",
    ]
    for cell in notebook["cells"]:
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        for token in forbidden:
            assert token not in source


@pytest.mark.unit
@pytest.mark.journey_system
def test_api_docs_readme_links_from_root_readme():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "docs/api/README.md" in readme
