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


def test_login_uses_configured_mfa_code_for_sms_prompt() -> None:
    """SessionManager should use ROBINHOOD_MFA_CODE for SMS/email prompts."""
    manager = SessionManager()
    manager.set_credentials("test_user", "test_pass")

    # We need to simulate rh.login calling input()
    def fake_login(username, password, store_session=True):
        import builtins

        # This will call the mock_input defined inside _login_with_device_verification
        return builtins.input("Enter SMS code: ")

    with (
        patch("open_stocks_mcp.tools.session_manager.rh.login", side_effect=fake_login),
        patch.dict("os.environ", {"ROBINHOOD_MFA_CODE": "123456"}),
        patch(
            "open_stocks_mcp.tools.session_manager.rh.load_user_profile",
            return_value={"id": "123"},
        ),
    ):
        # We expect this to fail initially because it returns "" currently,
        # and rh.login (fake_login) returns "" which is falsy.
        result = asyncio.run(manager.ensure_authenticated())
        assert result is True
        assert manager._is_authenticated is True


def test_login_keeps_device_approval_prompt_empty() -> None:
    """SessionManager should return "" for device approval prompts to let them wait."""
    manager = SessionManager()
    manager.set_credentials("test_user", "test_pass")

    captured_inputs = []

    def fake_login(username, password, store_session=True):
        import builtins

        val = builtins.input("Please approve the login on your device: ")
        captured_inputs.append(val)
        return True  # Simulate success after "waiting"

    with (
        patch("open_stocks_mcp.tools.session_manager.rh.login", side_effect=fake_login),
        patch(
            "open_stocks_mcp.tools.session_manager.rh.load_user_profile",
            return_value={"id": "123"},
        ),
    ):
        result = asyncio.run(manager.ensure_authenticated())
        assert result is True
        assert captured_inputs == [""]


def test_logout_reraises_exception_and_still_clears_state() -> None:
    """Logout failures should propagate to callers while still clearing local state."""
    manager = SessionManager()
    manager._is_authenticated = True
    manager.login_time = datetime.now()
    manager.last_successful_call = datetime.now()
    manager._failed_login_attempts = 1

    with (
        patch(
            "open_stocks_mcp.tools.session_manager.rh.logout",
            side_effect=RuntimeError("logout failure"),
        ),
        pytest.raises(RuntimeError, match="logout failure"),
    ):
        asyncio.run(manager.logout())

    assert manager._is_authenticated is False
    assert manager.login_time is None
    assert manager.last_successful_call is None
    assert manager._failed_login_attempts == 0
