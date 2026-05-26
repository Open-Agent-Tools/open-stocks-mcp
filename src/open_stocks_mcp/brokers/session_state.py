"""Session management for Robin Stocks authentication."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.brokers.session_mfa import (
    handle_login_prompt,
    login_with_device_verification,
    resolve_mfa_code,
)
from open_stocks_mcp.brokers.session_pickle import SessionPickleManager
from open_stocks_mcp.logging_config import logger


class SessionManager:
    """Manages Robin Stocks authentication session lifecycle."""

    def __init__(
        self,
        session_timeout_hours: int = 23,
        max_failed_attempts: int = 3,
        pickle_manager: SessionPickleManager | None = None,
    ) -> None:
        self.session_timeout_hours = session_timeout_hours
        self.max_failed_attempts = max_failed_attempts
        self.login_time: datetime | None = None
        self.last_successful_call: datetime | None = None
        self.username: str | None = None
        self.password: str | None = None
        self._lock = asyncio.Lock()
        self._is_authenticated = False
        self._failed_login_attempts = 0
        self._pickle = pickle_manager or SessionPickleManager()

    def set_credentials(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self._failed_login_attempts = 0

    def is_session_valid(self) -> bool:
        if not self._is_authenticated or not self.login_time:
            return False

        elapsed = datetime.now() - self.login_time
        if elapsed > timedelta(hours=self.session_timeout_hours):
            logger.info(f"Session expired after {elapsed}")
            return False

        return True

    def update_last_successful_call(self) -> None:
        self.last_successful_call = datetime.now()

    # -- Delegate pickle operations to SessionPickleManager --

    def _get_tokens_dir(self):  # type: ignore[no-untyped-def]
        return self._pickle._get_tokens_dir()

    def _get_pickle_file_path(self, pickle_name: str = "robinhood"):  # type: ignore[no-untyped-def]
        return self._pickle._get_pickle_file_path(pickle_name)

    def _get_encrypted_pickle_path(self, pickle_name: str = "robinhood"):  # type: ignore[no-untyped-def]
        return self._pickle._get_encrypted_pickle_path(pickle_name)

    def _get_fernet_key_path(self):  # type: ignore[no-untyped-def]
        return self._pickle._get_fernet_key_path()

    def _get_or_create_fernet_key(self) -> bytes:
        return self._pickle._get_or_create_fernet_key()

    def _encrypt_pickle_if_exists(self, pickle_name: str = "robinhood") -> None:
        self._pickle._encrypt_pickle_if_exists(pickle_name)

    def _decrypt_pickle_if_exists(self, pickle_name: str = "robinhood") -> bool:
        return self._pickle._decrypt_pickle_if_exists(pickle_name)

    def _clear_pickle_file(self, pickle_name: str = "robinhood") -> bool:
        return self._pickle._clear_pickle_file(pickle_name)

    def should_block_auth_retries(self) -> bool:
        return self._pickle.should_block_auth_retries()

    # -- Delegate MFA operations to session_mfa module --

    def _resolve_mfa_code(self) -> str:
        return resolve_mfa_code()

    def _handle_login_prompt(self, prompt: str = "") -> str:
        return handle_login_prompt(prompt)

    # -- Failed-attempt tracking --

    def _increment_failed_attempts(self) -> None:
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
        if self._failed_login_attempts > 0:
            logger.info(
                f"Resetting failed login attempts (was {self._failed_login_attempts})"
            )
            self._failed_login_attempts = 0

    # -- Authentication --

    async def ensure_authenticated(self) -> bool:
        async with self._lock:
            if self.is_session_valid():
                return True
            return await self._authenticate()

    async def _authenticate(self) -> bool:
        if not self.username or not self.password:
            logger.error("No credentials available for authentication")
            return False

        try:
            logger.info(f"Attempting to authenticate user: {self.username}")

            loop = asyncio.get_event_loop()

            try:
                login_result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        self._login_with_device_verification,
                        self.username,
                        self.password,
                    ),
                    timeout=150,
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

            user_profile = await loop.run_in_executor(None, rh.load_user_profile)

            if user_profile:
                self.login_time = datetime.now()
                self._is_authenticated = True
                self._reset_failed_attempts()
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
        return login_with_device_verification(self._pickle, username, password, timeout)

    async def refresh_session(self) -> bool:
        async with self._lock:
            logger.info("Forcing session refresh")
            self._is_authenticated = False
            self.login_time = None
            return await self._authenticate()

    def get_session_info(self) -> dict[str, Any]:
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
                self._failed_login_attempts = 0
                self._pickle.reset_clear_failures()

    def clear_session_cache(self) -> bool:
        return self._clear_pickle_file()

    async def force_fresh_login(self) -> bool:
        async with self._lock:
            logger.info("Forcing fresh login - clearing all cached authentication")

            self._is_authenticated = False
            self.login_time = None
            self.last_successful_call = None

            if self._clear_pickle_file():
                logger.info("Session cache cleared successfully")
            else:
                logger.warning("Failed to clear session cache - proceeding anyway")

            self._failed_login_attempts = 0

            logger.info("Attempting fresh authentication...")
            return await self._authenticate()


# Global session manager instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


async def ensure_authenticated_session() -> tuple[bool, str | None]:
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
