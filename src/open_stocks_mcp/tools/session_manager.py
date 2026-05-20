"""Session management for Robin Stocks authentication."""

import asyncio
import contextlib
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import robin_stocks.robinhood as rh
from cryptography.fernet import Fernet, InvalidToken

from open_stocks_mcp.logging_config import logger


class SessionManager:
    """Manages Robin Stocks authentication session lifecycle."""

    def __init__(self, session_timeout_hours: int = 23, max_failed_attempts: int = 3):
        """Initialize session manager.

        Args:
            session_timeout_hours: Hours before session is considered expired (default: 23)
            max_failed_attempts: Maximum failed login attempts before clearing pickle (default: 3)
        """
        self.session_timeout_hours = session_timeout_hours
        self.max_failed_attempts = max_failed_attempts
        self.login_time: datetime | None = None
        self.last_successful_call: datetime | None = None
        self.username: str | None = None
        self.password: str | None = None
        self._lock = asyncio.Lock()
        self._is_authenticated = False
        self._failed_login_attempts = 0
        self._consecutive_pickle_clear_failures = 0
        self._max_pickle_clear_failures = 3

    def set_credentials(self, username: str, password: str) -> None:
        """Store credentials for re-authentication.

        Args:
            username: Robinhood username
            password: Robinhood password
        """
        self.username = username
        self.password = password
        # Reset failed attempts when credentials change
        self._failed_login_attempts = 0

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

    def _get_tokens_dir(self) -> Path:
        """Get the tokens directory, creating it with restricted permissions if needed."""
        tokens_dir = Path.home() / ".tokens"
        tokens_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Ensure correct mode if dir already existed.
        if os.name != "nt":
            try:
                tokens_dir.chmod(0o700)
            except OSError as e:
                logger.warning(f"Could not set secure permissions on {tokens_dir}: {e}")
        return tokens_dir

    def _get_pickle_file_path(self, pickle_name: str = "robinhood") -> Path:
        """Get the path to the Robin Stocks pickle file.

        Args:
            pickle_name: Name of the pickle file (default: "robinhood")

        Returns:
            Path to the pickle file
        """
        return self._get_tokens_dir() / f"{pickle_name}.pickle"

    def _get_encrypted_pickle_path(self, pickle_name: str = "robinhood") -> Path:
        """Get path to the encrypted session pickle file."""
        return self._get_tokens_dir() / f"{pickle_name}.pickle.enc"

    def _get_fernet_key_path(self) -> Path:
        """Get path to the per-machine Fernet key file."""
        return self._get_tokens_dir() / ".session.key"

    def _get_or_create_fernet_key(self) -> bytes:
        """Return the Fernet key for this machine, generating one if absent."""
        key_path = self._get_fernet_key_path()
        if key_path.exists():
            return key_path.read_bytes()
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        key_path.chmod(0o600)
        return key

    def _encrypt_pickle_if_exists(self, pickle_name: str = "robinhood") -> None:
        """Encrypt the plaintext pickle written by robin-stocks and remove it."""
        pickle_path = self._get_pickle_file_path(pickle_name)
        if not pickle_path.exists():
            return
        try:
            key = self._get_or_create_fernet_key()
            ciphertext = Fernet(key).encrypt(pickle_path.read_bytes())
            enc_path = self._get_encrypted_pickle_path(pickle_name)
            enc_path.write_bytes(ciphertext)
            enc_path.chmod(0o600)
            pickle_path.unlink()
            logger.debug(f"Session pickle encrypted: {enc_path}")
        except Exception as e:
            logger.warning(
                f"Could not encrypt session pickle, hardening permissions: {e}"
            )
            # Fall back to permission hardening so the plaintext is at least owner-only
            with contextlib.suppress(Exception):
                pickle_path.chmod(0o600)

    def _decrypt_pickle_if_exists(self, pickle_name: str = "robinhood") -> bool:
        """Decrypt the encrypted session pickle so robin-stocks can read it.

        Returns:
            True if an encrypted pickle was decrypted, False if none existed.
        """
        enc_path = self._get_encrypted_pickle_path(pickle_name)
        if not enc_path.exists():
            return False
        try:
            key = self._get_or_create_fernet_key()
            plaintext = Fernet(key).decrypt(enc_path.read_bytes())
            pickle_path = self._get_pickle_file_path(pickle_name)
            pickle_path.write_bytes(plaintext)
            pickle_path.chmod(0o600)
            logger.debug(f"Session pickle decrypted for use: {pickle_path}")
            return True
        except InvalidToken:
            logger.warning(
                "Session pickle decryption failed (key mismatch or corrupt), treating as missing"
            )
            enc_path.unlink(missing_ok=True)
            return False
        except Exception as e:
            logger.warning(
                f"Could not decrypt session pickle, treating as missing: {e}"
            )
            enc_path.unlink(missing_ok=True)
            return False

    def _clear_pickle_file(self, pickle_name: str = "robinhood") -> bool:
        """Clear the Robin Stocks session pickle file and its encrypted counterpart.

        Args:
            pickle_name: Name of the pickle file to clear (default: "robinhood")

        Returns:
            True if files were removed or didn't exist, False if removal failed
        """
        try:
            pickle_path = self._get_pickle_file_path(pickle_name)
            enc_path = self._get_encrypted_pickle_path(pickle_name)
            cleared = False
            if pickle_path.exists():
                pickle_path.unlink()
                logger.info(f"Cleared pickle file: {pickle_path}")
                cleared = True
            else:
                logger.debug(f"Pickle file does not exist: {pickle_path}")
            if enc_path.exists():
                enc_path.unlink()
                logger.info(f"Cleared encrypted pickle file: {enc_path}")
                cleared = True
            if not cleared:
                logger.debug(f"No session files found for: {pickle_name}")
            self._consecutive_pickle_clear_failures = 0
            return True
        except Exception as e:
            self._consecutive_pickle_clear_failures += 1
            logger.error(f"Failed to clear pickle file: {e}")
            if (
                self._consecutive_pickle_clear_failures
                >= self._max_pickle_clear_failures
            ):
                logger.critical(
                    "Session cache clear failed %s consecutive times; authentication retries will be blocked until cache clear succeeds",
                    self._consecutive_pickle_clear_failures,
                )
            return False

    def should_block_auth_retries(self) -> bool:
        """Return True when persistent pickle clear failures make auth retries unsafe."""
        return (
            self._consecutive_pickle_clear_failures >= self._max_pickle_clear_failures
        )

    def _increment_failed_attempts(self) -> None:
        """Increment failed login attempts and clear pickle if threshold reached."""
        self._failed_login_attempts += 1
        logger.warning(
            f"Login attempt {self._failed_login_attempts} of {self.max_failed_attempts} failed"
        )

        if self._failed_login_attempts >= self.max_failed_attempts:
            logger.error(
                f"Maximum failed login attempts ({self.max_failed_attempts}) reached. Clearing session cache."
            )
            if self._clear_pickle_file():
                logger.info(
                    "Session cache cleared successfully. Next login will start fresh."
                )
            else:
                logger.error(
                    "Failed to clear session cache. Manual cleanup may be required."
                )

    def _reset_failed_attempts(self) -> None:
        """Reset failed login attempts counter on successful authentication."""
        if self._failed_login_attempts > 0:
            logger.info(
                f"Resetting failed login attempts (was {self._failed_login_attempts})"
            )
            self._failed_login_attempts = 0

    def _resolve_mfa_code(self) -> str:
        """Resolve MFA code from environment variable or interactive input.

        Returns:
            The resolved MFA code, or an empty string if not found.
        """
        # 1. Check environment variable first
        mfa_code = os.environ.get("ROBINHOOD_MFA_CODE", "").strip()
        if mfa_code:
            logger.info("Using MFA code from ROBINHOOD_MFA_CODE environment variable")
            return mfa_code

        # 2. Fall back to interactive prompt if in a TTY
        import sys

        if sys.stdin.isatty():
            try:
                # Use stderr for prompt to avoid polluting stdout in some environments
                sys.stderr.write("\nROBINHOOD MFA REQUIRED\n")
                sys.stderr.write("Enter verification code: ")
                sys.stderr.flush()
                return sys.stdin.readline().strip()
            except Exception as e:
                logger.error(f"Failed to read interactive MFA code: {e}")

        return ""

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

            # Use a custom login function that handles device verification with timeout
            try:
                login_result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        self._login_with_device_verification,
                        self.username,
                        self.password,
                    ),
                    timeout=150,  # 150 second timeout for entire login process
                )
            except TimeoutError:
                logger.error("Authentication timed out after 150 seconds")
                logger.info("This may indicate:")
                logger.info("1. Network connectivity issues")
                logger.info("2. Robinhood server problems")
                logger.info("3. Stuck waiting for MFA/device approval")
                logger.info("Try: Force fresh login to clear cache and retry")
                self._increment_failed_attempts()
                return False

            if not login_result:
                logger.error("Login failed - device verification may be required")
                self._increment_failed_attempts()
                return False

            # Verify login by making a test API call
            user_profile = await loop.run_in_executor(None, rh.load_user_profile)

            if user_profile:
                self.login_time = datetime.now()
                self._is_authenticated = True
                self._reset_failed_attempts()  # Reset counter on successful login
                logger.info(f"Successfully authenticated user: {self.username}")
                return True
            else:
                logger.error("Authentication failed: Could not retrieve user profile")
                self._increment_failed_attempts()
                return False

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self._increment_failed_attempts()
            return False

    def _login_with_device_verification(
        self, username: str, password: str, timeout: int = 120
    ) -> bool:
        """Handle Robin Stocks login with device verification support.

        Args:
            username: Robinhood username
            password: Robinhood password
            timeout: Login timeout in seconds (default: 120)

        Returns:
            True if login successful, False otherwise
        """
        import io
        from contextlib import redirect_stderr, redirect_stdout

        try:
            # Note: Signal-based timeout doesn't work in threads/async contexts
            # The asyncio.wait_for timeout in _authenticate() provides the timeout instead

            # Capture any output from Robin Stocks
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                # Override input function to handle prompts more gracefully
                builtins_dict = (
                    __builtins__
                    if isinstance(__builtins__, dict)
                    else __builtins__.__dict__
                )
                original_input = builtins_dict.get("input", input)

                def mock_input(prompt: str = "") -> str:
                    """Mock input function that handles various Robin Stocks prompts."""
                    logger.info(f"Robin Stocks prompt: {prompt}")

                    # Handle MFA code requests more gracefully
                    if any(
                        keyword in prompt.lower()
                        for keyword in [
                            "code",
                            "sms",
                            "email",
                            "verification",
                            "mfa",
                            "2fa",
                        ]
                    ):
                        logger.warning(f"MFA/Verification code required: {prompt}")
                        logger.info("Authentication requires MFA. This may indicate:")
                        logger.info("1. A new device needs verification")
                        logger.info("2. Session cache may be corrupted")
                        logger.info("3. Account has enhanced security enabled")
                        logger.info(
                            "Suggestion: Clear session cache and try fresh login"
                        )

                        # Attempt to resolve the code
                        return self._resolve_mfa_code()

                    # Handle device approval prompts
                    if any(
                        keyword in prompt.lower()
                        for keyword in [
                            "app",
                            "device",
                            "approval",
                            "notification",
                            "push",
                        ]
                    ):
                        logger.info(f"Device approval required: {prompt}")
                        logger.info(
                            "Please check your Robinhood mobile app and approve the device"
                        )
                        logger.info("Waiting for approval...")
                        return ""

                    # Handle any other prompts
                    logger.debug(f"Returning empty string for prompt: {prompt}")
                    return ""

                # Temporarily replace input function
                if isinstance(__builtins__, dict):
                    __builtins__["input"] = mock_input
                else:
                    __builtins__.input = mock_input  # type: ignore[assignment]

                try:
                    logger.info(f"Attempting login with {timeout}s timeout...")
                    # Restore any previously encrypted session so robin-stocks can reuse it
                    self._decrypt_pickle_if_exists()
                    # Attempt login with device verification handling
                    result = rh.login(username, password, store_session=True)

                    if result:
                        logger.info("Login successful")
                        return True
                    else:
                        logger.error("Login failed - authentication rejected")
                        return False

                except Exception as inner_e:
                    error_msg = str(inner_e)
                    logger.error(f"Login exception: {error_msg}")

                    # Provide more specific error guidance
                    if any(
                        keyword in error_msg.lower()
                        for keyword in [
                            "verification",
                            "device",
                            "challenge",
                            "code",
                            "mfa",
                            "2fa",
                        ]
                    ):
                        logger.error("Authentication requires additional verification")
                        logger.info("Recommended actions:")
                        logger.info(
                            "1. Check Robinhood mobile app for pending notifications"
                        )
                        logger.info("2. Approve device access if prompted")
                        logger.info(
                            "3. If issue persists, clear session cache and retry"
                        )
                        logger.info("4. Ensure account credentials are correct")
                    elif "timeout" in error_msg.lower():
                        logger.error("Login request timed out")
                        logger.info(
                            "This may indicate network issues or server problems"
                        )
                    else:
                        logger.error(f"Unexpected login error: {error_msg}")

                    return False
                finally:
                    # Restore input and re-encrypt any temporarily decrypted session.
                    if isinstance(__builtins__, dict):
                        __builtins__["input"] = original_input
                    else:
                        __builtins__.input = original_input
                    self._encrypt_pickle_if_exists()

            # Log any captured output for debugging
            stdout_content = stdout_buffer.getvalue()
            stderr_content = stderr_buffer.getvalue()

            if stdout_content.strip():
                logger.debug(f"Robin Stocks stdout: {stdout_content.strip()}")
            if stderr_content.strip():
                logger.debug(f"Robin Stocks stderr: {stderr_content.strip()}")

            return False

        except Exception as e:
            logger.error(f"Critical login error: {e}")
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
            "failed_login_attempts": self._failed_login_attempts,
            "max_failed_attempts": self.max_failed_attempts,
        }

        if self.login_time:
            elapsed = datetime.now() - self.login_time
            remaining = timedelta(hours=self.session_timeout_hours) - elapsed
            info["time_until_expiry"] = (
                str(remaining) if remaining.total_seconds() > 0 else "Expired"
            )

        return info

    async def logout(self) -> None:
        """Logout and clear session.

        Robin Stocks logout failures are logged and re-raised so callers can
        choose whether logout is best-effort or fail-hard. Local session state is
        always cleared before this method returns or raises.
        """
        async with self._lock:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, rh.logout)
                logger.info("Successfully logged out")
            except Exception as e:
                logger.error(f"Error during logout: {e}")
                raise
            finally:
                self._is_authenticated = False
                self.login_time = None
                self.last_successful_call = None
                # Reset failed attempts on logout
                self._failed_login_attempts = 0
                self._consecutive_pickle_clear_failures = 0

    def clear_session_cache(self) -> bool:
        """Manually clear the Robin Stocks session cache (pickle file).

        Returns:
            True if cache was cleared successfully, False otherwise
        """
        return self._clear_pickle_file()

    async def force_fresh_login(self) -> bool:
        """Force a completely fresh login by clearing cache and re-authenticating.

        This method is useful when authentication appears to be stuck or
        when MFA/device verification issues persist.

        Returns:
            True if fresh login successful, False otherwise
        """
        async with self._lock:
            logger.info("Forcing fresh login - clearing all cached authentication")

            # Clear session state
            self._is_authenticated = False
            self.login_time = None
            self.last_successful_call = None

            # Clear pickle file to force fresh authentication
            if self._clear_pickle_file():
                logger.info("Session cache cleared successfully")
            else:
                logger.warning("Failed to clear session cache - proceeding anyway")

            # Reset failed attempts for fresh start
            self._failed_login_attempts = 0

            # Attempt fresh authentication
            logger.info("Attempting fresh authentication...")
            return await self._authenticate()


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


async def force_fresh_authentication() -> tuple[bool, str | None]:
    """Force a completely fresh authentication by clearing all cached data.

    This function is useful when authentication appears stuck or when
    MFA/device verification issues persist.

    Returns:
        Tuple of (success, error_message)
    """
    manager = get_session_manager()

    try:
        logger.info("Forcing fresh authentication due to authentication issues")
        success = await manager.force_fresh_login()
        if success:
            return True, None
        else:
            return False, "Fresh authentication failed"
    except Exception as e:
        logger.error(f"Fresh authentication error: {e}")
        return False, str(e)
