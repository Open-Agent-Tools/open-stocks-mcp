"""Session management for Robin Stocks authentication."""

import asyncio
from datetime import datetime, timedelta

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger


class SessionManager:
    """Manages Robin Stocks authentication session lifecycle."""

    def __init__(self, session_timeout_hours: int = 23):
        """Initialize session manager.

        Args:
            session_timeout_hours: Hours before session is considered expired (default: 23)
        """
        self.session_timeout_hours = session_timeout_hours
        self.login_time: datetime | None = None
        self.last_successful_call: datetime | None = None
        self.username: str | None = None
        self.password: str | None = None
        self._lock = asyncio.Lock()
        self._is_authenticated = False

    def set_credentials(self, username: str, password: str) -> None:
        """Store credentials for re-authentication.

        Args:
            username: Robinhood username
            password: Robinhood password
        """
        self.username = username
        self.password = password

    def is_session_valid(self) -> bool:
        """Check if current session is still valid.

        Returns:
            True if session is valid, False otherwise
        """
        if not self._is_authenticated or not self.login_time:
            return False

        # Check if session has expired based on timeout
        elapsed = datetime.now() - self.login_time
        if elapsed > timedelta(hours=self.session_timeout_hours):
            logger.info(f"Session expired after {elapsed}")
            return False

        return True

    def update_last_successful_call(self) -> None:
        """Update timestamp of last successful API call."""
        self.last_successful_call = datetime.now()

    async def ensure_authenticated(self) -> bool:
        """Ensure session is authenticated, re-authenticating if necessary.

        Returns:
            True if authentication successful, False otherwise
        """
        async with self._lock:
            # Check if already authenticated and valid
            if self.is_session_valid():
                return True

            # Need to authenticate
            return await self._authenticate()

    async def _authenticate(self) -> bool:
        """Perform authentication with stored credentials.

        Returns:
            True if authentication successful, False otherwise
        """
        if not self.username or not self.password:
            logger.error("No credentials available for authentication")
            return False

        try:
            logger.info(f"Attempting to authenticate user: {self.username}")

            # Run synchronous login in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                rh.login,
                self.username,
                self.password,
                None,  # expires_in
                None,  # scope
                True,  # store_session
            )

            # Verify login by making a test API call
            user_profile = await loop.run_in_executor(None, rh.load_user_profile)

            if user_profile:
                self.login_time = datetime.now()
                self._is_authenticated = True
                logger.info(f"Successfully authenticated user: {self.username}")
                return True
            else:
                logger.error("Authentication failed: Could not retrieve user profile")
                return False

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    async def refresh_session(self) -> bool:
        """Force a new login session.

        Returns:
            True if refresh successful, False otherwise
        """
        async with self._lock:
            logger.info("Forcing session refresh")
            self._is_authenticated = False
            self.login_time = None
            return await self._authenticate()

    def get_session_info(self) -> dict:
        """Get current session information.

        Returns:
            Dictionary with session status and metadata
        """
        info = {
            "is_authenticated": self._is_authenticated,
            "is_valid": self.is_session_valid(),
            "username": self.username,
            "login_time": self.login_time.isoformat() if self.login_time else None,
            "last_successful_call": self.last_successful_call.isoformat()
            if self.last_successful_call
            else None,
            "session_timeout_hours": self.session_timeout_hours,
        }

        if self.login_time:
            elapsed = datetime.now() - self.login_time
            remaining = timedelta(hours=self.session_timeout_hours) - elapsed
            info["time_until_expiry"] = (
                str(remaining) if remaining.total_seconds() > 0 else "Expired"
            )

        return info

    async def logout(self) -> None:
        """Logout and clear session."""
        async with self._lock:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, rh.logout)
                logger.info("Successfully logged out")
            except Exception as e:
                logger.error(f"Error during logout: {e}")
            finally:
                self._is_authenticated = False
                self.login_time = None
                self.last_successful_call = None


# Global session manager instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance.

    Returns:
        The global SessionManager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


async def ensure_authenticated_session() -> tuple[bool, str | None]:
    """Ensure an authenticated session exists.

    Returns:
        Tuple of (success, error_message)
    """
    manager = get_session_manager()

    try:
        success = await manager.ensure_authenticated()
        if success:
            return True, None
        else:
            return False, "Authentication failed"
    except Exception as e:
        logger.error(f"Session authentication error: {e}")
        return False, str(e)
