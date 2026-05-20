"""Unit tests for session manager behavior."""

import asyncio
import builtins
import io
from contextlib import redirect_stderr
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from open_stocks_mcp.tools.session_manager import SessionManager

pytestmark = pytest.mark.unit


def test_is_session_valid_false_when_not_authenticated() -> None:
    manager = SessionManager(session_timeout_hours=1)

    assert manager.is_session_valid() is False


def test_is_session_valid_false_when_missing_login_time() -> None:
    manager = SessionManager(session_timeout_hours=1)
    manager._is_authenticated = True
    manager.login_time = None

    assert manager.is_session_valid() is False


def test_is_session_valid_false_when_expired() -> None:
    manager = SessionManager(session_timeout_hours=1)
    manager._is_authenticated = True
    manager.login_time = datetime.now() - timedelta(hours=2)

    assert manager.is_session_valid() is False


def test_is_session_valid_true_when_fresh() -> None:
    manager = SessionManager(session_timeout_hours=1)
    manager._is_authenticated = True
    manager.login_time = datetime.now() - timedelta(minutes=10)

    assert manager.is_session_valid() is True


def test_clear_pickle_file_removes_existing_file(tmp_path: Path) -> None:
    manager = SessionManager()
    pickle_path = tmp_path / "robinhood.pickle"
    pickle_path.write_text("session")

    with patch.object(manager, "_get_pickle_file_path", return_value=pickle_path):
        result = manager._clear_pickle_file()

    assert result is True
    assert not pickle_path.exists()


def test_clear_pickle_file_returns_true_when_missing(tmp_path: Path) -> None:
    manager = SessionManager()
    pickle_path = tmp_path / "robinhood.pickle"

    with patch.object(manager, "_get_pickle_file_path", return_value=pickle_path):
        result = manager._clear_pickle_file()

    assert result is True


def test_clear_pickle_file_returns_false_on_unlink_error(tmp_path: Path) -> None:
    manager = SessionManager()
    pickle_path = tmp_path / "robinhood.pickle"
    pickle_path.write_text("session")

    with (
        patch.object(manager, "_get_pickle_file_path", return_value=pickle_path),
        patch.object(Path, "unlink", side_effect=PermissionError("denied")),
    ):
        result = manager._clear_pickle_file()

    assert result is False


@pytest.mark.asyncio
async def test_authenticate_returns_false_without_credentials() -> None:
    manager = SessionManager()

    result = await manager._authenticate()

    assert result is False


@pytest.mark.asyncio
async def test_authenticate_success_sets_session_state() -> None:
    manager = SessionManager()
    manager.set_credentials("user", "pass")

    with (
        patch.object(manager, "_login_with_device_verification", return_value=True),
        patch(
            "open_stocks_mcp.tools.session_manager.rh.load_user_profile",
            return_value={"id": "123"},
        ),
    ):
        result = await manager._authenticate()

    assert result is True
    assert manager._is_authenticated is True
    assert manager.login_time is not None


@pytest.mark.asyncio
async def test_authenticate_returns_false_when_login_rejected() -> None:
    manager = SessionManager(max_failed_attempts=5)
    manager.set_credentials("user", "pass")

    with patch.object(manager, "_login_with_device_verification", return_value=False):
        result = await manager._authenticate()

    assert result is False
    assert manager._failed_login_attempts == 1


@pytest.mark.asyncio
async def test_authenticate_returns_false_when_profile_missing() -> None:
    manager = SessionManager(max_failed_attempts=5)
    manager.set_credentials("user", "pass")

    with (
        patch.object(manager, "_login_with_device_verification", return_value=True),
        patch(
            "open_stocks_mcp.tools.session_manager.rh.load_user_profile",
            return_value=None,
        ),
    ):
        result = await manager._authenticate()

    assert result is False
    assert manager._failed_login_attempts == 1


@pytest.mark.asyncio
async def test_authenticate_returns_false_on_exception() -> None:
    manager = SessionManager(max_failed_attempts=5)
    manager.set_credentials("user", "pass")

    with patch.object(
        manager,
        "_login_with_device_verification",
        side_effect=RuntimeError("invalid credentials"),
    ):
        result = await manager._authenticate()

    assert result is False
    assert manager._failed_login_attempts == 1


def test_login_with_device_verification_success_and_restores_input() -> None:
    manager = SessionManager()
    original_input = builtins.input

    with patch(
        "open_stocks_mcp.tools.session_manager.rh.login", return_value={"ok": True}
    ):
        result = manager._login_with_device_verification("user", "pass")

    assert result is True
    assert builtins.input is original_input


def test_login_with_device_verification_mfa_prompt_path_and_restores_input() -> None:
    manager = SessionManager()
    original_input = builtins.input

    def fake_login(_username: str, _password: str, store_session: bool = True):
        _ = builtins.input("Enter verification code: ")
        return None

    with patch("open_stocks_mcp.tools.session_manager.rh.login", side_effect=fake_login):
        result = manager._login_with_device_verification("user", "pass")

    assert result is False
    assert builtins.input is original_input


def test_login_with_device_verification_invalid_credentials_path() -> None:
    manager = SessionManager()

    with patch(
        "open_stocks_mcp.tools.session_manager.rh.login",
        side_effect=RuntimeError("invalid credentials"),
    ):
        result = manager._login_with_device_verification("user", "pass")

    assert result is False


@pytest.mark.asyncio
async def test_refresh_session_reauthenticates_after_invalidating_state() -> None:
    manager = SessionManager()
    manager._is_authenticated = True
    manager.login_time = datetime.now()

    with patch.object(manager, "_authenticate", new=AsyncMock(return_value=True)) as auth:
        result = await manager.refresh_session()

    assert result is True
    auth.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_authenticated_concurrent_calls_only_authenticate_once() -> None:
    manager = SessionManager()
    calls = 0

    async def fake_authenticate() -> bool:
        nonlocal calls
        calls += 1
        manager._is_authenticated = True
        manager.login_time = datetime.now()
        return True

    with patch.object(manager, "_authenticate", side_effect=fake_authenticate):
        results = await asyncio.gather(
            manager.ensure_authenticated(),
            manager.ensure_authenticated(),
        )

    assert results == [True, True]
    assert calls == 1


@pytest.mark.asyncio
async def test_logout_clears_session_state() -> None:
    manager = SessionManager()
    manager._is_authenticated = True
    manager.login_time = datetime.now()
    manager.last_successful_call = datetime.now()
    manager._failed_login_attempts = 2

    with patch("open_stocks_mcp.tools.session_manager.rh.logout"):
        await manager.logout()

    assert manager._is_authenticated is False
    assert manager.login_time is None
    assert manager.last_successful_call is None
    assert manager._failed_login_attempts == 0


@pytest.mark.asyncio
async def test_logout_reraises_exception_and_still_clears_state() -> None:
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
        await manager.logout()

    assert manager._is_authenticated is False
    assert manager.login_time is None
    assert manager.last_successful_call is None
    assert manager._failed_login_attempts == 0


def test_interactive_mfa_prompt_uses_original_stderr_when_stderr_is_redirected() -> (
    None
):
    """Interactive MFA prompt should bypass redirected stderr capture."""
    manager = SessionManager()

    fake_stdin = io.StringIO("654321\n")
    fake_stdin.isatty = lambda: True  # type: ignore[attr-defined]
    original_stderr = io.StringIO()
    redirected_stderr = io.StringIO()

    with (
        patch.dict("os.environ", {}, clear=True),
        patch("sys.stdin", fake_stdin),
        patch("sys.__stderr__", original_stderr),
        redirect_stderr(redirected_stderr),
    ):
        code = manager._resolve_mfa_code()

    assert code == "654321"
    assert "ROBINHOOD MFA REQUIRED" in original_stderr.getvalue()
    assert "Enter verification code:" in original_stderr.getvalue()
    assert "ROBINHOOD MFA REQUIRED" not in redirected_stderr.getvalue()
