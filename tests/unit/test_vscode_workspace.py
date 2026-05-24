"""Tests for VS Code workspace configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent.parent
VSCODE = ROOT / ".vscode"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_vscode_workspace_files_are_valid_json() -> None:
    for filename in ("launch.json", "settings.json", "extensions.json"):
        assert _load_json(VSCODE / filename)


@pytest.mark.unit
def test_vscode_launch_runs_http_server_with_debug_flag() -> None:
    launch = _load_json(VSCODE / "launch.json")

    config = next(
        item
        for item in launch["configurations"]
        if item["name"] == "Run MCP server (HTTP)"
    )

    assert config["type"] == "python"
    assert config["request"] == "launch"
    assert config["module"] == "open_stocks_mcp.server.app"
    assert config["console"] == "integratedTerminal"
    assert config["env"]["PYTHONPATH"] == "${workspaceFolder}/src"
    assert config["args"] == [
        "--transport",
        "http",
        "--host",
        "127.0.0.1",
        "--port",
        "3001",
        "--debug",
    ]


@pytest.mark.unit
def test_vscode_settings_configure_uv_python_ruff_pytest_and_mypy() -> None:
    settings = _load_json(VSCODE / "settings.json")

    assert (
        settings["python.defaultInterpreterPath"]
        == "${workspaceFolder}/.venv/bin/python"
    )
    assert settings["python.testing.pytestEnabled"] is True
    assert settings["python.testing.unittestEnabled"] is False
    assert settings["python.testing.pytestArgs"] == ["tests"]
    assert settings["[python]"]["editor.defaultFormatter"] == "charliermarsh.ruff"
    assert settings["ruff.lint.run"] == "onSave"
    assert settings["mypy-type-checker.args"] == ["--config-file=pyproject.toml"]


@pytest.mark.unit
def test_vscode_extensions_recommend_python_pylance_ruff_and_mypy() -> None:
    extensions = _load_json(VSCODE / "extensions.json")

    recommendations = set(extensions["recommendations"])

    assert {
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff",
        "ms-python.mypy-type-checker",
    } <= recommendations
