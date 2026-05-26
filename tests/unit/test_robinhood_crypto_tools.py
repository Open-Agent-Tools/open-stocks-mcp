"""Unit tests guarding against accidental crypto tool surface reintroduction."""

import importlib.util
from pathlib import Path

import pytest


@pytest.mark.unit
@pytest.mark.journey_system
def test_crypto_placeholder_module_is_absent() -> None:
    # Anchor to the project root to avoid false positives if run from a subdirectory
    project_root = Path(__file__).parent.parent.parent
    crypto_module_path = project_root / "src/open_stocks_mcp/tools/robinhood_crypto_tools.py"

    assert not crypto_module_path.exists(), (
        f"Crypto placeholder module must stay deleted at {crypto_module_path}"
    )

    # Idiomatic check for module absence
    spec = importlib.util.find_spec("open_stocks_mcp.tools.robinhood_crypto_tools")
    assert spec is None, "robinhood_crypto_tools should not be importable"


@pytest.mark.unit
@pytest.mark.journey_system
def test_server_does_not_import_crypto_placeholder_module() -> None:
    project_root = Path(__file__).parent.parent.parent
    server_app_path = project_root / "src/open_stocks_mcp/server/app.py"
    assert server_app_path.exists(), f"server/app.py must exist at {server_app_path}"

    source = server_app_path.read_text(encoding="utf-8")
    assert "robinhood_crypto_tools" not in source, (
        "Crypto placeholder module should not be imported in server/app.py"
    )
