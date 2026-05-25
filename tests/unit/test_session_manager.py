"""Unit tests for session manager behavior."""

import asyncio
import builtins
import io
from contextlib import redirect_stderr
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from open_stocks_mcp.tools import session_manager as session_manager_module
from open_stocks_mcp.tools.session_manager import SessionManager

pytestmark = pytest.mark.unit


def test_is_session_valid_false_when_not_authenticated() -> None:
    manager = SessionManager()

    assert manager.is_session_valid() is False


def test_is_session_valid_false_when_login_time_missing() -> None:
    manager = SessionManager()
    manager._is_authenticated = True
    manager.login_time = None

    assert manager.is_session_valid() is False


def test_is_session_valid_false_when_expired() -> None:
    manager = SessionManager(session_timeout_hours=1)
    manager._is_authenticated = True
    manager.login_time = datetime.now() - timedelta(hours=2)

    assert manager.is_session_valid() is False


def test_is_session_valid_true_when_authenticated_and_fresh() -> None:
    manager = SessionManager(session_timeout_hours=1)
    manager._is_authenticated = True
    manager.login_time = datetime.now() - timedelta(minutes=10)

    assert manager.is_session_valid() is True


def test_clear_pickle_file_success_when_file_exists(tmp_path: Path) -> None:
    manager = SessionManager()
    pickle_path = tmp_path / "robinhood.pickle"
    pickle_path.write_text("session")

    with patch.object(manager, "_get_pickle_file_path", return_value=pickle_path):
        assert manager._clear_pickle_file() is True

    assert not pickle_path.exists()


def test_clear_pickle_file_success_when_file_missing(tmp_path: Path) -> None:
    manager = SessionManager()
    pickle_path = tmp_path / "robinhood.pickle"

    with patch.object(manager, "_get_pickle_file_path", return_value=pickle_path):
        assert manager._clear_pickle_file() is True


def test_clear_pickle_file_false_when_unlink_raises(tmp_path: Path) -> None:
    manager = SessionManager()
    pickle_path = tmp_path / "robinhood.pickle"
    pickle_path.write_text("session")

    with (
        patch.object(manager, "_get_pickle_file_path", return_value=pickle_path),
        patch.object(Path, "unlink", side_effect=PermissionError("denied")),
    ):
        assert manager._clear_pickle_file() is False


def test_handle_login_prompt_returns_mfa_code_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = SessionManager()
    monkeypatch.setenv("ROBINHOOD_MFA_CODE", "123456")

    result = manager._handle_login_prompt("Please enter the verification code: ")

    assert result == "123456"


def test_handle_login_prompt_returns_empty_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = SessionManager()
    monkeypatch.delenv("ROBINHOOD_MFA_CODE", raising=False)

    result = manager._handle_login_prompt("Enter SMS code: ")

    assert result == ""


def test_handle_login_prompt_returns_empty_for_device_approval() -> None:
    manager = SessionManager()

    result = manager._handle_login_prompt("Approve this device in the Robinhood app")

    assert result == ""


@pytest.mark.asyncio
async def test_authenticate_false_with_missing_credentials() -> None:
    manager = SessionManager()

    result = await manager._authenticate()

    assert result is False


@pytest.mark.asyncio
async def test_authenticate_success_with_login_and_profile() -> None:
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
async def test_authenticate_false_when_login_returns_false() -> None:
    manager = SessionManager()
    manager.set_credentials("user", "pass")

    with patch.object(manager, "_login_with_device_verification", return_value=False):
        result = await manager._authenticate()

    assert result is False
    assert manager._is_authenticated is False
    assert manager._failed_login_attempts == 1


@pytest.mark.asyncio
async def test_authenticate_false_when_profile_missing() -> None:
    manager = SessionManager()
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
async def test_authenticate_false_when_login_raises() -> None:
    manager = SessionManager()
    manager.set_credentials("user", "pass")

    with patch.object(
        manager,
        "_login_with_device_verification",
        side_effect=RuntimeError("invalid credentials"),
    ):
        result = await manager._authenticate()

    assert result is False
    assert manager._failed_login_attempts == 1


def test_login_with_device_verification_success_restores_input() -> None:
    manager = SessionManager()
    original_input = builtins.input

    with patch("open_stocks_mcp.tools.session_manager.rh.login", return_value=True):
        result = manager._login_with_device_verification("user", "pass")

    assert result is True
    assert builtins.input is original_input


def test_login_with_device_verification_mfa_prompt_returns_false_and_restores_input() -> (
    None
):
    manager = SessionManager()
    original_input = builtins.input

    def fake_login(_username: str, _password: str, store_session: bool = True) -> bool:
        _ = store_session
        return bool(builtins.input("Enter verification code: "))

    with patch(
        "open_stocks_mcp.tools.session_manager.rh.login", side_effect=fake_login
    ):
        result = manager._login_with_device_verification("user", "pass")

    assert result is False
    assert builtins.input is original_input


def test_login_with_device_verification_invalid_credentials_exception_restores_input() -> (
    None
):
    manager = SessionManager()
    original_input = builtins.input

    with patch(
        "open_stocks_mcp.tools.session_manager.rh.login",
        side_effect=RuntimeError("invalid credentials"),
    ):
        result = manager._login_with_device_verification("user", "pass")

    assert result is False
    assert builtins.input is original_input


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


@pytest.mark.asyncio
async def test_refresh_session_reauthenticates() -> None:
    manager = SessionManager()
    manager._is_authenticated = True
    manager.login_time = datetime.now()

    async def fake_auth() -> bool:
        manager._is_authenticated = True
        manager.login_time = datetime.now()
        return True

    with patch.object(manager, "_authenticate", side_effect=fake_auth):
        result = await manager.refresh_session()

    assert result is True
    assert manager._is_authenticated is True
    assert manager.login_time is not None


@pytest.mark.asyncio
async def test_force_fresh_login_clears_cache_then_authenticates() -> None:
    manager = SessionManager()
    manager._is_authenticated = True
    manager.login_time = datetime.now()
    manager.last_successful_call = datetime.now()
    manager._failed_login_attempts = 2

    async def fake_auth() -> bool:
        manager._is_authenticated = True
        manager.login_time = datetime.now()
        return True

    with (
        patch.object(manager, "_clear_pickle_file", return_value=True),
        patch.object(manager, "_authenticate", side_effect=fake_auth),
    ):
        result = await manager.force_fresh_login()

    assert result is True
    assert manager._failed_login_attempts == 0


@pytest.mark.asyncio
async def test_ensure_authenticated_concurrent_calls_only_authenticate_once() -> None:
    manager = SessionManager()
    manager.set_credentials("user", "pass")
    call_count = 0

    async def fake_auth() -> bool:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0)
        manager._is_authenticated = True
        manager.login_time = datetime.now()
        return True

    with patch.object(manager, "_authenticate", side_effect=fake_auth):
        first, second = await asyncio.gather(
            manager.ensure_authenticated(),
            manager.ensure_authenticated(),
        )

    assert first is True
    assert second is True
    assert call_count == 1


def test_interactive_mfa_prompt_uses_original_stderr_when_stderr_is_redirected() -> (
    None
):
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


@pytest.mark.journey_account
@pytest.mark.exception_test
def test_ensure_authenticated_handles_expired_session_without_unhandled_exception() -> (
    None
):
    manager = SessionManager(session_timeout_hours=0)
    manager.set_credentials("user", "pass")
    manager._is_authenticated = True
    manager.login_time = datetime.now()

    with patch.object(manager, "_authenticate", return_value=False):
        result = asyncio.run(manager.ensure_authenticated())

    assert result is False


@pytest.mark.journey_account
@pytest.mark.exception_test
def test_ensure_authenticated_handles_invalid_credentials_login_failure() -> None:
    manager = SessionManager()
    manager.set_credentials("user", "pass")

    with (
        patch(
            "open_stocks_mcp.tools.session_manager.rh.login",
            side_effect=Exception("invalid credentials"),
        ),
        patch("open_stocks_mcp.tools.session_manager.rh.load_user_profile"),
    ):
        result = asyncio.run(manager.ensure_authenticated())

    assert result is False
    assert manager._is_authenticated is False
    assert manager._failed_login_attempts == 1


@pytest.mark.asyncio
@pytest.mark.journey_account
@pytest.mark.exception_test
async def test_ensure_authenticated_session_returns_error_tuple_on_exception() -> None:
    fake_manager = SessionManager()
    with (
        patch.object(
            fake_manager,
            "ensure_authenticated",
            side_effect=Exception("invalid credentials"),
        ),
        patch.object(
            session_manager_module,
            "get_session_manager",
            return_value=fake_manager,
        ),
    ):
        success, error = await session_manager_module.ensure_authenticated_session()

    assert success is False
    assert error == "invalid credentials"
