"""Tests for developer tooling and contributor documentation."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent.parent
VSCODE = ROOT / ".vscode"


def _load_jsonc(path: Path) -> dict[str, Any]:
    content = re.sub(r"//[^\n]*", "", path.read_text(encoding="utf-8"))
    return json.loads(content)


@pytest.mark.unit
def test_vscode_workspace_files_exist_and_parse() -> None:
    settings = _load_jsonc(VSCODE / "settings.json")
    launch = _load_jsonc(VSCODE / "launch.json")
    tasks = _load_jsonc(VSCODE / "tasks.json")

    assert settings["python.testing.pytestEnabled"] is True
    assert settings["[python]"]["editor.defaultFormatter"] == "charliermarsh.ruff"

    launch_names = {config["name"] for config in launch["configurations"]}
    assert {"Run MCP server (HTTP)", "Pytest: current file"} <= launch_names

    task_labels = {task["label"] for task in tasks["tasks"]}
    assert {
        "uv sync",
        "ruff: fix",
        "ruff: format",
        "mypy",
        "pytest: fast",
    } <= task_labels


@pytest.mark.unit
def test_contributing_guide_exists_and_mentions_debugging_recipes() -> None:
    guide = ROOT / "CONTRIBUTING.md"

    content = guide.read_text(encoding="utf-8")

    assert guide.stat().st_size >= 1024
    for expected in (
        "## Setup",
        "## Testing",
        "## Debugging",
        ".vscode/launch.json",
    ):
        assert expected in content


@pytest.mark.unit
def test_schwab_status_version_matches_pyproject() -> None:
    pyproject = ROOT / "pyproject.toml"
    schwab_status = ROOT / "SCHWAB_STATUS.md"

    pyproject_data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    version = pyproject_data["project"]["version"]
    expected = f"**Version**: v{version}"

    content = schwab_status.read_text(encoding="utf-8")
    assert expected in content
