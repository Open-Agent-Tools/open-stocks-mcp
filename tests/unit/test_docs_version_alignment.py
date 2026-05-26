"""Verify the README Current Status version matches the canonical package version."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _readme_status_version() -> str:
    text = (ROOT / "README.md").read_text()
    m = re.search(r"Current Status:\s*v([\d.]+[^\s]*)", text)
    assert m, "Could not find 'Current Status: v...' line in README.md"
    return m.group(1).rstrip(" -")


def _pyproject_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def _package_version() -> str:
    import open_stocks_mcp

    return open_stocks_mcp.__version__


@pytest.mark.journey_system
class TestDocsVersionAlignment:
    def test_readme_matches_pyproject(self) -> None:
        assert _readme_status_version() == _pyproject_version()

    def test_readme_matches_package(self) -> None:
        assert _readme_status_version() == _package_version()

    def test_pyproject_matches_package(self) -> None:
        assert _pyproject_version() == _package_version()
