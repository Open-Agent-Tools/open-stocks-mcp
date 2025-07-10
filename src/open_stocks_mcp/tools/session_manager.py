"""Session management for Robin Stocks authentication."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

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

            # Run synchronous login in executor with device verification handling
            loop = asyncio.get_event_loop()

            # Use a custom login function that handles device verification
            login_result = await loop.run_in_executor(
                None, self._login_with_device_verification, self.username, self.password
            )

            if not login_result:
                logger.error("Login failed - device verification may be required")
                return False

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

    def _login_with_device_verification(self, username: str, password: str) -> bool:
        """Handle Robin Stocks login with device verification support.

        Args:
            username: Robinhood username
            password: Robinhood password

        Returns:
            True if login successful, False otherwise
        """
        import io
        from contextlib import redirect_stderr, redirect_stdout

        try:
            # Capture any output from Robin Stocks
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                # Override input function to simulate automatic approval
                builtins_dict = (
                    __builtins__
                    if isinstance(__builtins__, dict)
                    else __builtins__.__dict__
                )
                original_input = builtins_dict.get("input", input)

                def mock_input(prompt: str = "") -> str:
                    """Mock input function that logs prompts and simulates automatic approval."""
                    logger.info(f"Device verification prompt: {prompt}")

                    # If this is asking for a verification code, we can't provide it
                    if any(
                        keyword in prompt.lower()
                        for keyword in ["code", "sms", "email", "verification"]
                    ):
                        logger.error(
                            "Interactive verification code required - cannot proceed in headless mode"
                        )
                        raise Exception("Interactive verification required")

                    # For device approval prompts, simulate waiting
                    if any(
                        keyword in prompt.lower()
                        for keyword in ["app", "device", "approval", "notification"]
                    ):
                        logger.info("Waiting for device approval...")
                        # Robin Stocks will handle the device approval workflow
                        return ""

                    # Default case - return empty string
                    return ""

                # Temporarily replace input function
                if isinstance(__builtins__, dict):
                    __builtins__["input"] = mock_input
                else:
                    __builtins__.input = mock_input  # type: ignore[assignment]

                try:
                    # Attempt login with device verification handling
                    result = rh.login(username, password, store_session=True)

                    # Restore original input function
                    if isinstance(__builtins__, dict):
                        __builtins__["input"] = original_input
                    else:
                        __builtins__.input = original_input

                    if result:
                        logger.info("Login successful with device verification")
                        return True
                    else:
                        logger.error("Login failed")
                        return False

                except Exception as inner_e:
                    # Restore original input function
                    if isinstance(__builtins__, dict):
                        __builtins__["input"] = original_input
                    else:
                        __builtins__.input = original_input

                    error_msg = str(inner_e)

                    # Check if this is a device verification issue
                    if any(
                        keyword in error_msg.lower()
                        for keyword in ["verification", "device", "challenge", "code"]
                    ):
                        logger.error(f"Device verification required: {error_msg}")
                        logger.info(
                            "This account requires device verification. Please:"
                        )
                        logger.info(
                            "1. Check your Robinhood mobile app for verification prompts"
                        )
                        logger.info("2. Approve the device if prompted")
                        logger.info("3. Try again after verification")
                    else:
                        logger.error(f"Login error: {error_msg}")

                    return False

            # Log any captured output
            stdout_content = stdout_buffer.getvalue()
            stderr_content = stderr_buffer.getvalue()

            if stdout_content:
                logger.info(f"Robin Stocks output: {stdout_content}")
            if stderr_content:
                logger.warning(f"Robin Stocks errors: {stderr_content}")

            return False

        except Exception as e:
            logger.error(f"Device verification login failed: {e}")
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

    def get_session_info(self) -> dict[str, Any]:
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
