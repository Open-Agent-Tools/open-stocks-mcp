"""Guard tests for broker architecture: session_manager must live under brokers/."""

import importlib

import pytest


def test_new_module_is_importable() -> None:
    mod = importlib.import_module("open_stocks_mcp.brokers.robinhood_session")
    assert hasattr(mod, "SessionManager")
    assert hasattr(mod, "get_session_manager")
    assert hasattr(mod, "ensure_authenticated_session")
    assert hasattr(mod, "force_fresh_authentication")


def test_old_module_is_gone() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("open_stocks_mcp.tools.session_manager")
