"""MCP tools for Robin Stocks authentication and session management."""

import robin_stocks.robinhood as rh
from mcp import types

from open_stocks_mcp.logging_config import logger


async def login_robinhood(
    username: str, password: str, mfa_code: str
) -> types.TextContent:
    """
    Login to Robinhood API with user-provided credentials.

    Args:
        username: Robinhood account username (email)
        password: Robinhood account password
        mfa_code: 6-digit MFA code received via SMS

    Returns:
        TextContent: Login status message
    """
    logger.info(f"Attempting login for user: {username}")

    try:
        # Attempt login with robin-stocks using the provided MFA code
        login_response = rh.login(
            username=username,
            password=password,
            mfa_code=mfa_code,
            store_session=False,  # Don't store in pickle file
        )

        if login_response:
            logger.info(f"Successfully logged in user: {username}")
            return types.TextContent(
                type="text",
                text=f"✅ Successfully logged into Robinhood\nUser: {username}\nSession expires in 24 hours",
            )
        else:
            logger.error(f"Login failed for user: {username}")
            return types.TextContent(
                type="text",
                text="❌ Login failed: Invalid credentials or authentication error",
            )

    except Exception as e:
        logger.error(f"Login error: {e!s}")
        return types.TextContent(type="text", text=f"❌ Login error: {e!s}")


async def logout_robinhood() -> types.TextContent:
    """
    Logout from Robinhood API.

    Returns:
        TextContent: Logout status message
    """
    # TODO: Implement logout tool
    logger.info("Logout tool called")
    raise NotImplementedError("Logout tool not implemented")


async def auth_status() -> types.TextContent:
    """
    Check Robinhood authentication status.

    Returns:
        TextContent: Authentication status information
    """
    # TODO: Implement auth status tool
    logger.info("Auth status tool called")
    raise NotImplementedError("Auth status tool not implemented")


async def account_info() -> types.TextContent:
    """
    Get Robinhood account information.

    Returns:
        TextContent: Account information or error message
    """
    # TODO: Implement account info tool
    logger.info("Account info tool called")
    raise NotImplementedError("Account info tool not implemented")
