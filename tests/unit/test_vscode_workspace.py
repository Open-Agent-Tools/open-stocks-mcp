"""Tests for VS Code workspace configuration files."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def _load_json(rel_path: str) -> dict:
    path = REPO_ROOT / rel_path
    assert path.exists(), f"{rel_path} does not exist"
    return json.loads(path.read_text())


def test_launch_json_is_valid_json() -> None:
    """launch.json must be parseable as standard JSON (no JSONC comments)."""
    _load_json(".vscode/launch.json")


def test_launch_json_has_http_debug_configuration() -> None:
    """launch.json must contain a debug configuration for the HTTP server."""
    data = _load_json(".vscode/launch.json")
    configs = data.get("configurations", [])
    assert configs, "launch.json has no configurations"

    debug_config = next(
        (c for c in configs if "--debug" in c.get("args", [])),
        None,
    )
    assert debug_config is not None, "No configuration with --debug arg found"
    args = debug_config["args"]
    assert "--transport" in args, "--transport missing from debug config args"
    assert "http" in args, "http transport not specified in debug config args"
    assert "--port" in args, "--port missing from debug config args"


def test_launch_json_uses_module_launch() -> None:
    """launch.json debug config must use module-style launch for open_stocks_mcp.server.app."""
    data = _load_json(".vscode/launch.json")
    configs = data.get("configurations", [])
    debug_config = next(
        (c for c in configs if "--debug" in c.get("args", [])),
        None,
    )
    assert debug_config is not None
    assert debug_config.get("module") == "open_stocks_mcp.server.app"
    assert debug_config.get("console") == "integratedTerminal"


def test_settings_json_is_valid_json() -> None:
    """settings.json must be parseable as standard JSON."""
    _load_json(".vscode/settings.json")


def test_settings_json_has_python_interpreter() -> None:
    """settings.json must point to the .venv Python interpreter."""
    data = _load_json(".vscode/settings.json")
    interp = data.get("python.defaultInterpreterPath", "")
    assert ".venv" in interp, f"Expected .venv in interpreter path, got: {interp}"


def test_settings_json_enables_pytest() -> None:
    """settings.json must enable pytest discovery."""
    data = _load_json(".vscode/settings.json")
    assert data.get("python.testing.pytestEnabled") is True
    assert "tests" in str(data.get("python.testing.pytestArgs", []))


def test_settings_json_configures_ruff() -> None:
    """settings.json must configure Ruff as the Python formatter."""
    data = _load_json(".vscode/settings.json")
    python_settings = data.get("[python]", {})
    formatter = python_settings.get("editor.defaultFormatter", "")
    assert "ruff" in formatter, f"Expected ruff formatter, got: {formatter}"


def test_settings_json_enables_mypy() -> None:
    """settings.json must enable mypy type checking."""
    data = _load_json(".vscode/settings.json")
    assert data.get("mypy-type-checker.enabled") is True


def test_extensions_json_is_valid_json() -> None:
    """extensions.json must be parseable as standard JSON (no JSONC comments)."""
    _load_json(".vscode/extensions.json")


def test_extensions_json_recommends_required_extensions() -> None:
    """extensions.json must recommend Python, Pylance, Ruff, and mypy extensions."""
    data = _load_json(".vscode/extensions.json")
    recs = set(data.get("recommendations", []))
    required = {
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff",
        "ms-python.mypy-type-checker",
    }
    missing = required - recs
    assert not missing, f"Missing required recommendations: {missing}"
