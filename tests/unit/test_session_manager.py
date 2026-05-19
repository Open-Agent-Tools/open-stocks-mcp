"""Unit tests for session manager behavior."""

import asyncio
from datetime import datetime
from unittest.mock import patch

import pytest

from open_stocks_mcp.tools.session_manager import SessionManager


def test_logout_clears_session_state() -> None:
    """Logout should clear authentication state and timestamps."""
    manager = SessionManager()
    manager._is_authenticated = True
    manager.login_time = datetime.now()
    manager.last_successful_call = datetime.now()
    manager._failed_login_attempts = 2

    with patch("open_stocks_mcp.tools.session_manager.rh.logout"):
        asyncio.run(manager.logout())

    assert manager._is_authenticated is False
    assert manager.login_time is None
    assert manager.last_successful_call is None
    assert manager._failed_login_attempts == 0


def test_logout_reraises_exception_and_still_clears_state() -> None:
    """Logout failures should propagate to callers while still clearing local state."""
    manager = SessionManager()
    manager._is_authenticated = True
    manager.login_time = datetime.now()
    manager.last_successful_call = datetime.now()
    manager._failed_login_attempts = 1

    with patch(
        "open_stocks_mcp.tools.session_manager.rh.logout",
        side_effect=RuntimeError("logout failure"),
    ), pytest.raises(RuntimeError, match="logout failure"):
        asyncio.run(manager.logout())

    assert manager._is_authenticated is False
    assert manager.login_time is None
    assert manager.last_successful_call is None
    assert manager._failed_login_attempts == 0
