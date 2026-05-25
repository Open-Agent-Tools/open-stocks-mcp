"""MFA resolution, login-prompt handling, and device-verification login flow."""

import io
import os
from contextlib import redirect_stderr, redirect_stdout

import robin_stocks.robinhood as rh

from open_stocks_mcp.brokers.session_pickle import SessionPickleManager
from open_stocks_mcp.logging_config import logger


def resolve_mfa_code() -> str:
    mfa_code = os.environ.get("ROBINHOOD_MFA_CODE", "").strip()
    if mfa_code:
        logger.info("Using MFA code from ROBINHOOD_MFA_CODE environment variable")
        return mfa_code

    import sys

    if sys.stdin.isatty():
        try:
            prompt_stream = getattr(sys, "__stderr__", None) or sys.stderr
            prompt_stream.write("\nROBINHOOD MFA REQUIRED\n")
            prompt_stream.write("Enter verification code: ")
            prompt_stream.flush()
            return sys.stdin.readline().strip()
        except Exception as e:
            logger.error(f"Failed to read interactive MFA code: {e}")

    return ""


def handle_login_prompt(prompt: str = "") -> str:
    logger.info(f"Robin Stocks prompt: {prompt}")

    prompt_lower = prompt.lower()

    if any(
        keyword in prompt_lower
        for keyword in ["code", "sms", "email", "verification", "mfa", "2fa"]
    ):
        logger.warning(f"MFA/Verification code required: {prompt}")
        mfa_code = os.environ.get("ROBINHOOD_MFA_CODE", "").strip()
        if mfa_code:
            logger.info("Using ROBINHOOD_MFA_CODE from environment for MFA prompt")
            return mfa_code

        logger.info("Authentication requires MFA. This may indicate:")
        logger.info("1. A new device needs verification")
        logger.info("2. Session cache may be corrupted")
        logger.info("3. Account has enhanced security enabled")
        logger.info("Suggestion: Clear session cache and try fresh login")
        logger.warning(
            "Set ROBINHOOD_MFA_CODE env var with the time-sensitive code before retrying."
        )
        return ""

    if any(
        keyword in prompt_lower
        for keyword in ["app", "device", "approval", "notification", "push"]
    ):
        logger.info(f"Device approval required: {prompt}")
        logger.info("Please check your Robinhood mobile app and approve the device")
        logger.info("Waiting for approval...")
        return ""

    logger.debug(f"Returning empty string for prompt: {prompt}")
    return ""


def login_with_device_verification(
    session_pickle: SessionPickleManager,
    username: str,
    password: str,
    timeout: int = 120,
) -> bool:
    try:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            builtins_dict = (
                __builtins__
                if isinstance(__builtins__, dict)
                else __builtins__.__dict__
            )
            original_input = builtins_dict.get("input", input)

            def mock_input(prompt: str = "") -> str:
                return handle_login_prompt(prompt)

            if isinstance(__builtins__, dict):
                __builtins__["input"] = mock_input
            else:
                __builtins__.input = mock_input  # type: ignore[assignment]

            try:
                logger.info(f"Attempting login with {timeout}s timeout...")
                session_pickle._decrypt_pickle_if_exists()
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
                    logger.info("3. If issue persists, clear session cache and retry")
                    logger.info("4. Ensure account credentials are correct")
                elif "timeout" in error_msg.lower():
                    logger.error("Login request timed out")
                    logger.info("This may indicate network issues or server problems")
                else:
                    logger.error(f"Unexpected login error: {error_msg}")

                return False
            finally:
                if isinstance(__builtins__, dict):
                    __builtins__["input"] = original_input
                else:
                    __builtins__.input = original_input
                session_pickle._encrypt_pickle_if_exists()

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
