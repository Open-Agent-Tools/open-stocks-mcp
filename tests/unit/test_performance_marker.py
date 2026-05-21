"""Tests for performance benchmark marker isolation."""

from __future__ import annotations

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
PERFORMANCE_SKIP_REASON = (
    "performance test; set RUN_PERFORMANCE=1 or pass '-m performance' to enable"
)

_PYTESTER_CONFTEST = dedent(f"""
    import os
    import pytest
    from typing import Any

    PERFORMANCE_SKIP_REASON = {PERFORMANCE_SKIP_REASON!r}

    def pytest_configure(config: Any) -> None:
        config.addinivalue_line(
            "markers",
            "performance: marks tests as performance/benchmark tests "
            "(skipped by default; opt in with '-m performance' or RUN_PERFORMANCE=1)",
        )

    def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
        markexpr = config.option.markexpr or ""
        if "performance" in markexpr or os.environ.get("RUN_PERFORMANCE"):
            return
        skip_performance = pytest.mark.skip(reason=PERFORMANCE_SKIP_REASON)
        for item in items:
            if list(item.iter_markers(name="performance")):
                item.add_marker(skip_performance)
""")

_PYTESTER_MODULE = dedent("""
    import pytest

    @pytest.mark.performance
    def test_marked():
        pass

    def test_unmarked():
        pass
""")


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
def test_performance_marker_registered_by_conftest() -> None:
    added_markers: list[tuple[str, str]] = []
    config = SimpleNamespace(
        addinivalue_line=lambda name, value: added_markers.append((name, value))
    )

    shared_conftest.pytest_configure(config)

    assert (
        "markers",
        "performance: marks tests as performance/benchmark tests "
        "(skipped by default; opt in with '-m performance' or RUN_PERFORMANCE=1)",
    ) in added_markers


@pytest.mark.unit
@pytest.mark.journey_system
def test_performance_tests_are_skipped_without_explicit_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RUN_PERFORMANCE", raising=False)
    config = SimpleNamespace(option=SimpleNamespace(markexpr="not slow"))
    performance_item = DummyItem({"performance"})
    unmarked_item = DummyItem(set())

    shared_conftest.pytest_collection_modifyitems(
        config, [performance_item, unmarked_item]
    )

    assert len(performance_item.added_markers) == 1
    assert performance_item.added_markers[0].kwargs["reason"] == PERFORMANCE_SKIP_REASON
    assert unmarked_item.added_markers == []


@pytest.mark.unit
@pytest.mark.journey_system
@pytest.mark.parametrize(
    ("markexpr", "run_performance"),
    [
        ("performance", None),
        ("not performance", None),
        ("not slow", "1"),
    ],
)
def test_performance_tests_are_not_skipped_when_explicitly_selected(
    monkeypatch: pytest.MonkeyPatch, markexpr: str, run_performance: str | None
) -> None:
    if run_performance is None:
        monkeypatch.delenv("RUN_PERFORMANCE", raising=False)
    else:
        monkeypatch.setenv("RUN_PERFORMANCE", run_performance)
    item = DummyItem({"performance"})
    config = SimpleNamespace(option=SimpleNamespace(markexpr=markexpr))

    shared_conftest.pytest_collection_modifyitems(config, [item])

    assert item.added_markers == []


@pytest.mark.unit
@pytest.mark.journey_system
def test_pytester_bare_run_skips_performance(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(_PYTESTER_CONFTEST)
    pytester.makepyfile(_PYTESTER_MODULE)

    result = pytester.runpytest()

    result.assert_outcomes(passed=1, skipped=1)


@pytest.mark.unit
@pytest.mark.journey_system
def test_pytester_explicit_m_performance_selects_marked(
    pytester: pytest.Pytester,
) -> None:
    pytester.makeconftest(_PYTESTER_CONFTEST)
    pytester.makepyfile(_PYTESTER_MODULE)

    result = pytester.runpytest("-m", "performance")

    result.assert_outcomes(passed=1, deselected=1)


@pytest.mark.unit
@pytest.mark.journey_system
def test_performance_benchmark_collection_nodeids() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "performance",
            "--co",
            "tests/performance",
            "-qq",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    for nodeid in (
        "tests/performance/test_mcp_tool_benchmarks.py::test_benchmark_account_info",
        "tests/performance/test_mcp_tool_benchmarks.py::test_benchmark_portfolio",
        "tests/performance/test_mcp_tool_benchmarks.py::test_benchmark_stock_price",
    ):
        assert nodeid in result.stdout


@pytest.mark.unit
@pytest.mark.journey_system
def test_performance_docs_are_present() -> None:
    for relative_path in ("README.md", "CLAUDE.md"):
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "performance" in content
        assert "uv run pytest -m performance tests/performance -v" in content
