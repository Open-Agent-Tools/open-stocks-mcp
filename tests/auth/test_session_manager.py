"""Tests for session_manager module."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import pytest

from open_stocks_mcp.tools.session_manager import SessionManager, get_session_manager


class TestSessionManager:
    """Test SessionManager class."""

    @pytest.fixture
    def session_manager(self) -> Any:
        """Create a fresh SessionManager instance."""
        return SessionManager()

    def test_init(self, session_manager: Any) -> None:
        """Test SessionManager initialization."""
        assert session_manager.session_timeout_hours == 23
        assert session_manager.login_time is None
        assert session_manager.last_successful_call is None
        assert session_manager.username is None
        assert session_manager.password is None
        assert not session_manager._is_authenticated

    def test_set_credentials(self, session_manager: Any) -> None:
        """Test setting credentials."""
        session_manager.set_credentials("testuser", "testpass")
        assert session_manager.username == "testuser"
        assert session_manager.password == "testpass"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    def test_is_session_valid_not_authenticated(self, session_manager: Any) -> None:
        """Test session validity when not authenticated."""
        assert not session_manager.is_session_valid()

    def test_is_session_valid_authenticated(self, session_manager: Any) -> None:
        """Test session validity when authenticated."""
        session_manager._is_authenticated = True
        session_manager.login_time = datetime.now()
        assert session_manager.is_session_valid()

    def test_is_session_valid_expired(self, session_manager: Any) -> None:
        """Test session validity when expired."""
        session_manager._is_authenticated = True
        # Set login time to 24 hours ago
        session_manager.login_time = datetime.now() - timedelta(hours=24)
        assert not session_manager.is_session_valid()

    def test_update_last_successful_call(self, session_manager: Any) -> None:
        """Test updating last successful call timestamp."""
        session_manager.update_last_successful_call()
        assert session_manager.last_successful_call is not None
        assert isinstance(session_manager.last_successful_call, datetime)

    @pytest.mark.asyncio
    async def test_ensure_authenticated_already_valid(
        self, session_manager: Any
    ) -> None:
        """Test ensure_authenticated when session is already valid."""
        session_manager._is_authenticated = True
        session_manager.login_time = datetime.now()

        result = await session_manager.ensure_authenticated()
        assert result is True

    @pytest.mark.asyncio
    async def test_ensure_authenticated_needs_auth(
        self, session_manager: Any, mocker: Any
    ) -> None:
        """Test ensure_authenticated when authentication is needed."""
        session_manager.set_credentials("testuser", "testpass")

        # Mock the Robin Stocks functions
        mocker.patch("robin_stocks.robinhood.login", return_value=True)
        mocker.patch(
            "robin_stocks.robinhood.load_user_profile",
            return_value={"username": "testuser"},
        )

        result = await session_manager.ensure_authenticated()
        assert result is True
        assert session_manager._is_authenticated is True
        assert session_manager.login_time is not None

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_ensure_authenticated_no_credentials(
        self, session_manager: Any
    ) -> None:
        """Test ensure_authenticated without credentials."""
        result = await session_manager.ensure_authenticated()
        assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_success(
        self, session_manager: Any, mocker: Any
    ) -> None:
        """Test successful authentication."""
        session_manager.set_credentials("testuser", "testpass")

        mocker.patch("robin_stocks.robinhood.login", return_value=True)
        mocker.patch(
            "robin_stocks.robinhood.load_user_profile",
            return_value={"username": "testuser"},
        )

        result = await session_manager._authenticate()
        assert result is True
        assert session_manager._is_authenticated is True

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_authenticate_failure(
        self, session_manager: Any, mocker: Any
    ) -> None:
        """Test authentication failure."""
        session_manager.set_credentials("testuser", "testpass")

        mocker.patch(
            "robin_stocks.robinhood.login", side_effect=Exception("Login failed")
        )

        result = await session_manager._authenticate()
        assert result is False
        assert not session_manager._is_authenticated

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_authenticate_no_profile(
        self, session_manager: Any, mocker: Any
    ) -> None:
        """Test authentication when profile retrieval fails."""
        session_manager.set_credentials("testuser", "testpass")

        mocker.patch("robin_stocks.robinhood.login", return_value=True)
        mocker.patch("robin_stocks.robinhood.load_user_profile", return_value=None)

        result = await session_manager._authenticate()
        assert result is False

    @pytest.mark.asyncio
    async def test_refresh_session(self, session_manager: Any, mocker: Any) -> None:
        """Test refreshing session."""
        session_manager.set_credentials("testuser", "testpass")
        session_manager._is_authenticated = True
        session_manager.login_time = datetime.now()

        mocker.patch("robin_stocks.robinhood.login", return_value=True)
        mocker.patch(
            "robin_stocks.robinhood.load_user_profile",
            return_value={"username": "testuser"},
        )

        result = await session_manager.refresh_session()
        assert result is True
        assert session_manager._is_authenticated is True

    def test_get_session_info_not_authenticated(self, session_manager: Any) -> None:
        """Test getting session info when not authenticated."""
        info = session_manager.get_session_info()

        assert info["is_authenticated"] is False
        assert info["is_valid"] is False
        assert info["username"] is None
        assert info["login_time"] is None
        assert info["session_timeout_hours"] == 23

    def test_get_session_info_authenticated(self, session_manager: Any) -> None:
        """Test getting session info when authenticated."""
        session_manager.set_credentials("testuser", "testpass")
        session_manager._is_authenticated = True
        session_manager.login_time = datetime.now()

        info = session_manager.get_session_info()

        assert info["is_authenticated"] is True
        assert info["is_valid"] is True
        assert info["username"] == "testuser"
        assert info["login_time"] is not None
        assert "time_until_expiry" in info

    def test_get_session_info_expired(self, session_manager: Any) -> None:
        """Test getting session info when expired."""
        session_manager._is_authenticated = True
        session_manager.login_time = datetime.now() - timedelta(hours=25)

        info = session_manager.get_session_info()

        assert info["is_authenticated"] is True
        assert info["is_valid"] is False
        assert info["time_until_expiry"] == "Expired"

    @pytest.mark.asyncio
    async def test_logout(self, session_manager: Any, mocker: Any) -> None:
        """Test logout functionality."""
        session_manager._is_authenticated = True
        session_manager.login_time = datetime.now()

        mocker.patch("robin_stocks.robinhood.logout")

        await session_manager.logout()

        assert not session_manager._is_authenticated
        assert session_manager.login_time is None
        assert session_manager.last_successful_call is None

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    async def test_logout_with_error(self, session_manager: Any, mocker: Any) -> None:
        """Test logout with error still clears session."""
        session_manager._is_authenticated = True
        session_manager.login_time = datetime.now()

        mocker.patch(
            "robin_stocks.robinhood.logout", side_effect=Exception("Logout error")
        )

        await session_manager.logout()

        # Session should still be cleared despite error
        assert not session_manager._is_authenticated
        assert session_manager.login_time is None


class TestSessionManagerGlobal:
    """Test global session manager functionality."""

    def test_get_session_manager_singleton(self) -> None:
        """Test that get_session_manager returns singleton."""
        manager1 = get_session_manager()
        manager2 = get_session_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_concurrent_authentication(self, mocker: Any) -> None:
        """Test concurrent authentication requests."""
        manager = SessionManager()
        manager.set_credentials("testuser", "testpass")

        # Mock slow authentication
        async def slow_auth(*args: Any, **kwargs: Any) -> Any:
            await asyncio.sleep(0.1)
            return {"username": "testuser"}

        mocker.patch("robin_stocks.robinhood.login", return_value=True)
        mock_profile = mocker.patch("robin_stocks.robinhood.load_user_profile")
        mock_profile.side_effect = slow_auth

        # Run multiple concurrent authentication attempts
        results = await asyncio.gather(
            manager.ensure_authenticated(),
            manager.ensure_authenticated(),
            manager.ensure_authenticated(),
        )

        # All should succeed
        assert all(results)

        # But authentication should only happen once
        assert mock_profile.call_count == 1
