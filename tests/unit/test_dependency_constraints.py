"""Regression tests for downstream runtime dependency constraints."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent


def _project_dependencies() -> dict[str, str]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]
    return {
        dependency.split("~=", maxsplit=1)[0].split(">=", maxsplit=1)[0]: dependency
        for dependency in dependencies
    }


@pytest.mark.unit
def test_broker_and_http_dependencies_use_compatible_release_pins() -> None:
    dependencies = _project_dependencies()

    assert dependencies["robin-stocks"] == "robin-stocks~=3.4.0"
    assert dependencies["schwab-py"] == "schwab-py~=1.5.0"
    assert dependencies["fastapi"] == "fastapi~=0.128.0"
    assert dependencies["uvicorn"] == "uvicorn~=0.40.0"
