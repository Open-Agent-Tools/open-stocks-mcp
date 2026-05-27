"""Tests for rate-limited marker isolation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace
from typing import Any

import pytest

import tests.conftest as shared_conftest

pytest_plugins = ("pytester",)

ROOT = Path(__file__).parent.parent.parent

_PYTESTER_CONFTEST = dedent("""
    import os
    import pytest
    from typing import Any

    RATE_LIMITED_SKIP_REASON = "rate_limited test; pass -m rate_limited to run it"

    def pytest_configure(config: Any) -> None:
        config.addinivalue_line(
            "markers",
            "rate_limited: marks tests that may hit rate-limited endpoints "
            "(skipped by default; opt in with -m rate_limited)",
        )

    def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
        markexpr = config.option.markexpr or ""
        if "rate_limited" in markexpr or os.environ.get("RUN_RATE_LIMITED"):
            return
        skip_rate_limited = pytest.mark.skip(reason=RATE_LIMITED_SKIP_REASON)
        for item in items:
            if list(item.iter_markers(name="rate_limited")):
                item.add_marker(skip_rate_limited)
""")

_PYTESTER_MODULE = dedent("""
    import pytest

    @pytest.mark.rate_limited
    def test_marked():
        pass

    def test_unmarked():
        pass
""")


def _config_with_markexpr(markexpr: str) -> SimpleNamespace:
    return SimpleNamespace(
        option=SimpleNamespace(markexpr=markexpr),
        getoption=lambda name, default=False: default,
    )


class DummyItem:
    """Small pytest item double for marker hook tests."""

    def __init__(self, marker_names: set[str]) -> None:
        self.marker_names = marker_names
        self.added_markers: list[Any] = []

    def iter_markers(self, name: str | None = None) -> list[SimpleNamespace]:
        markers = [SimpleNamespace(name=marker) for marker in self.marker_names]
        if name is None:
            return markers
        return [marker for marker in markers if marker.name == name]

    def add_marker(self, marker: Any) -> None:
        self.added_markers.append(marker)


@pytest.mark.unit
@pytest.mark.journey_system
def test_rate_limited_marker_registered_by_conftest() -> None:
    added_markers: list[tuple[str, str]] = []
    config = SimpleNamespace(
        addinivalue_line=lambda name, value: added_markers.append((name, value))
    )

    shared_conftest.pytest_configure(config)

    assert (
        "markers",
        "rate_limited: marks tests that may hit live endpoints with rate limit risk "
        "(skipped by default; opt in with '-m rate_limited' or RUN_RATE_LIMITED=1)",
    ) in added_markers


@pytest.mark.unit
@pytest.mark.journey_system
def test_rate_limited_tests_are_skipped_without_explicit_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RUN_RATE_LIMITED", raising=False)
    config = _config_with_markexpr("not slow")
    rate_limited_item = DummyItem({"rate_limited"})
    unmarked_item = DummyItem(set())

    shared_conftest.pytest_collection_modifyitems(
        config, [rate_limited_item, unmarked_item]
    )

    assert len(rate_limited_item.added_markers) == 1
    assert "rate_limited test" in rate_limited_item.added_markers[0].kwargs["reason"]
    assert unmarked_item.added_markers == []


@pytest.mark.unit
@pytest.mark.journey_system
@pytest.mark.parametrize(
    ("markexpr", "run_rate_limited"),
    [
        ("rate_limited", None),
        ("not rate_limited", None),
        ("not slow", "1"),
    ],
)
def test_rate_limited_tests_are_not_skipped_when_explicitly_selected(
    monkeypatch: pytest.MonkeyPatch, markexpr: str, run_rate_limited: str | None
) -> None:
    if run_rate_limited is None:
        monkeypatch.delenv("RUN_RATE_LIMITED", raising=False)
    else:
        monkeypatch.setenv("RUN_RATE_LIMITED", run_rate_limited)
    item = DummyItem({"rate_limited"})
    config = _config_with_markexpr(markexpr)

    shared_conftest.pytest_collection_modifyitems(config, [item])

    assert item.added_markers == []


@pytest.mark.unit
@pytest.mark.journey_system
@pytest.mark.slow
def test_rate_limited_collection_finds_live_api_tests() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-m",
            "rate_limited",
            "tests/integration/test_basic_api.py",
            "tests/server/test_server_login_flow.py",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "test_basic_api.py" in result.stdout
    assert "test_server_login_flow.py" in result.stdout


@pytest.mark.unit
@pytest.mark.journey_system
@pytest.mark.slow
def test_rate_limited_collection_nodeids() -> None:
    """Assert the exact set of live-API tests selected by -m rate_limited."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-m",
            "rate_limited",
            "-q",
            "tests/integration/test_basic_api.py",
            "tests/server/test_server_login_flow.py",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    # Check for presence of expected tests
    assert "test_get_account_info" in result.stdout
    assert "test_get_portfolio" in result.stdout
    assert "test_get_positions" in result.stdout
    assert "test_placeholder" in result.stdout

    # Check for absence of excluded tests
    assert "test_api_error_handling" not in result.stdout

    # Also check count to be sure no extra tests are selected
    count = sum(
        1
        for line in result.stdout.splitlines()
        if "::" in line and not line.startswith("no tests ran")
    )

    assert count == 4, f"Expected 4 tests, found {count}. Output:\n{result.stdout}"


@pytest.mark.unit
@pytest.mark.journey_system
def test_rate_limited_docs_are_present() -> None:
    for relative_path in ("README.md", "CLAUDE.md"):
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "rate_limited" in content


@pytest.mark.unit
@pytest.mark.journey_system
@pytest.mark.slow
def test_run_rate_limited_env_can_include_marked_tests() -> None:
    env = {**os.environ, "RUN_RATE_LIMITED": "1"}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "tests/integration/test_basic_api.py",
            "tests/server/test_server_login_flow.py",
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "<Class TestBasicIntegration>" in result.stdout
    assert "<Class TestServerLoginFlow>" in result.stdout


@pytest.mark.unit
@pytest.mark.journey_system
def test_pytester_bare_run_skips_rate_limited(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(_PYTESTER_CONFTEST)
    pytester.makepyfile(_PYTESTER_MODULE)

    result = pytester.runpytest()

    result.assert_outcomes(passed=1, skipped=1)


@pytest.mark.unit
@pytest.mark.journey_system
def test_pytester_explicit_m_rate_limited_selects_marked(
    pytester: pytest.Pytester,
) -> None:
    pytester.makeconftest(_PYTESTER_CONFTEST)
    pytester.makepyfile(_PYTESTER_MODULE)

    result = pytester.runpytest("-m", "rate_limited")

    result.assert_outcomes(passed=1, deselected=1)


@pytest.mark.unit
@pytest.mark.journey_system
def test_pytester_explicit_m_not_rate_limited_selects_unmarked(
    pytester: pytest.Pytester,
) -> None:
    pytester.makeconftest(_PYTESTER_CONFTEST)
    pytester.makepyfile(_PYTESTER_MODULE)

    result = pytester.runpytest("-m", "not rate_limited")

    result.assert_outcomes(passed=1, deselected=1)

@pytest.mark.unit
def test_subprocess_rate_limited_marker_tests_are_marked_slow() -> None:
    """Ensure subprocess tests are marked slow to avoid running in fast sessions."""
    from tests.unit.test_rate_limited_marker import (
        test_rate_limited_collection_finds_live_api_tests,
        test_rate_limited_collection_nodeids,
        test_run_rate_limited_env_can_include_marked_tests,
    )

    for test_func in [
        test_rate_limited_collection_finds_live_api_tests,
        test_rate_limited_collection_nodeids,
        test_run_rate_limited_env_can_include_marked_tests,
    ]:
        markers = {m.name for m in getattr(test_func, "pytestmark", [])}
        assert "slow" in markers, f"{test_func.__name__} is missing @pytest.mark.slow"
