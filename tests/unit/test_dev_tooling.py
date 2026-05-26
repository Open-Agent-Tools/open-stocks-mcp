"""Tests for developer tooling and contributor documentation."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).parent.parent.parent
VSCODE = ROOT / ".vscode"
MYPY_DEV_REQUIREMENT = "mypy>=2.1.0"
MYPY_PRE_COMMIT_REPO = "https://github.com/pre-commit/mirrors-mypy"
MYPY_PRE_COMMIT_REV = "v2.1.0"
MYPY_PRE_COMMIT_EXCLUDE = r"^(examples|tests)/"


def _load_jsonc(path: Path) -> dict[str, Any]:
    content = re.sub(r"//[^\n]*", "", path.read_text(encoding="utf-8"))
    return json.loads(content)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


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


@pytest.mark.unit
def test_mypy_dev_tooling_targets_2_1_0() -> None:
    pyproject_data = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert (
        MYPY_DEV_REQUIREMENT
        in pyproject_data["project"]["optional-dependencies"]["dev"]
    )
    assert MYPY_DEV_REQUIREMENT in pyproject_data["dependency-groups"]["dev"]

    pre_commit = _load_yaml(ROOT / ".pre-commit-config.yaml")
    mypy_repo = next(
        repo for repo in pre_commit["repos"] if repo["repo"] == MYPY_PRE_COMMIT_REPO
    )
    assert mypy_repo["rev"] == MYPY_PRE_COMMIT_REV
    assert mypy_repo["hooks"][0]["exclude"] == MYPY_PRE_COMMIT_EXCLUDE


@pytest.mark.unit
def test_dependency_floors_and_pre_commit_revisions() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pre_commit = yaml.safe_load(
        (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    )

    project_dependencies = set(pyproject["project"]["dependencies"])
    optional_dev_dependencies = set(
        pyproject["project"]["optional-dependencies"]["dev"]
    )
    group_dev_dependencies = set(pyproject["dependency-groups"]["dev"])

    assert "httpx>=0.28.1" in project_dependencies
    for dep in (
        "pytest>=9.0.3",
        "pytest-mock>=3.15.1",
        "ruff>=0.15.14",
        "pre-commit>=4.6.0",
        "httpx>=0.28.1",
    ):
        assert dep in optional_dev_dependencies
        assert dep in group_dev_dependencies
    assert "pytest-cov>=7.1.0" in group_dev_dependencies

    repo_revs = {repo["repo"]: repo["rev"] for repo in pre_commit["repos"]}
    assert repo_revs["https://github.com/astral-sh/ruff-pre-commit"] == "v0.15.14"
    assert repo_revs["https://github.com/pre-commit/pre-commit-hooks"] == "v6.0.0"
