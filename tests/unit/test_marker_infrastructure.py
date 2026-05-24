"""Validation tests for Phase 8 test marker infrastructure."""

import tomllib
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).parent.parent.parent / "pyproject.toml"
REQUIRED_MARKERS = {"rate_limited", "live_market", "performance", "auth_required"}
DEFAULT_EXCLUDED = {"live_market"}


def _load_pytest_config() -> dict:
    with open(PYPROJECT, "rb") as fh:
        return tomllib.load(fh)["tool"]["pytest"]["ini_options"]


# ---------------------------------------------------------------------------
# Marker registration
# ---------------------------------------------------------------------------


def test_required_markers_registered():
    cfg = _load_pytest_config()
    registered = {m.split(":")[0].strip() for m in cfg["markers"]}
    missing = REQUIRED_MARKERS - registered
    assert not missing, f"Markers not registered in pyproject.toml: {missing}"


def test_rate_limited_marker_description():
    cfg = _load_pytest_config()
    rate_limited = next(m for m in cfg["markers"] if m.startswith("rate_limited"))
    assert "rate limit" in rate_limited.lower()


def test_live_market_marker_description():
    cfg = _load_pytest_config()
    live_market = next(m for m in cfg["markers"] if m.startswith("live_market"))
    assert "live" in live_market.lower() or "market" in live_market.lower()


def test_performance_marker_description():
    cfg = _load_pytest_config()
    perf = next(m for m in cfg["markers"] if m.startswith("performance"))
    assert "performance" in perf.lower() or "benchmark" in perf.lower()


def test_auth_required_marker_description():
    cfg = _load_pytest_config()
    auth = next(m for m in cfg["markers"] if m.startswith("auth_required"))
    assert "auth" in auth.lower()


# ---------------------------------------------------------------------------
# Default addopts exclusions
# ---------------------------------------------------------------------------


def test_addopts_leaves_rate_limited_to_conftest_hook():
    cfg = _load_pytest_config()
    addopts = cfg.get("addopts", [])
    addopts_str = " ".join(addopts) if isinstance(addopts, list) else str(addopts)
    assert "not rate_limited" not in addopts_str, (
        "rate_limited tests are skipped by tests/conftest.py so "
        "RUN_RATE_LIMITED=1 can include them"
    )


def test_addopts_excludes_live_market():
    cfg = _load_pytest_config()
    addopts = cfg.get("addopts", [])
    addopts_str = " ".join(addopts) if isinstance(addopts, list) else str(addopts)
    assert "not live_market" in addopts_str, (
        "addopts must exclude live_market tests by default"
    )


def test_addopts_leaves_performance_to_conftest_hook():
    cfg = _load_pytest_config()
    addopts = cfg.get("addopts", [])
    addopts_str = " ".join(addopts) if isinstance(addopts, list) else str(addopts)
    assert "not performance" not in addopts_str, (
        "performance tests are skipped by tests/conftest.py so "
        "RUN_PERFORMANCE=1 can include them"
    )


def test_addopts_has_strict_markers():
    cfg = _load_pytest_config()
    addopts = cfg.get("addopts", [])
    addopts_str = " ".join(addopts) if isinstance(addopts, list) else str(addopts)
    assert "--strict-markers" in addopts_str


# ---------------------------------------------------------------------------
# Marker taxonomy completeness
# ---------------------------------------------------------------------------


def test_all_default_excluded_markers_have_descriptions():
    cfg = _load_pytest_config()
    registered = {m.split(":")[0].strip(): m for m in cfg["markers"]}
    for marker in DEFAULT_EXCLUDED:
        assert marker in registered, f"Marker '{marker}' missing from registry"
        assert ":" in registered[marker], (
            f"Marker '{marker}' must have a description (use 'name: description' format)"
        )


# ---------------------------------------------------------------------------
# Sample tests demonstrating marker behaviour
# (These will be collected only when explicitly requested)
# ---------------------------------------------------------------------------


@pytest.mark.rate_limited
def test_rate_limited_sample_excluded_by_default():
    """Would call a live broker API — excluded from default pytest runs."""
    assert True


@pytest.mark.live_market
def test_live_market_sample_excluded_by_default():
    """Would require an active market connection — excluded from default pytest runs."""
    assert True


@pytest.mark.performance
def test_performance_sample_excluded_by_default():
    """Would run a benchmark — excluded from default pytest runs."""
    assert True


@pytest.mark.auth_required
def test_auth_required_sample():
    """Would require ROBINHOOD_USERNAME/PASSWORD in env — opt-in only."""
    assert True
