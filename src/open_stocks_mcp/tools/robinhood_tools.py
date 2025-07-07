"""MCP tools for Robin Stocks authentication and session management."""

import os
import robin_stocks.robinhood as rh
from mcp import types

from open_stocks_mcp.logging_config import logger


async def auto_login() -> types.TextContent:
    """
    Automatically attempt to login to Robinhood and request MFA if needed.
    
    This should be called first by the agent to initiate the login process.
    It checks for environment credentials and either:
    1. Reports missing credentials, or
    2. Initiates login and requests MFA from user
    
    Returns:
        TextContent: Either credential setup instructions or MFA request
    """
    # Get credentials from environment
    username = os.getenv("ROBINHOOD_USERNAME")
    password = os.getenv("ROBINHOOD_PASSWORD")
    
    # Check if credentials are available
    if not username or not password:
        missing = []
        if not username:
            missing.append("ROBINHOOD_USERNAME")
        if not password:
            missing.append("ROBINHOOD_PASSWORD")
            
        logger.warning(f"Missing credentials: {', '.join(missing)}")
        return types.TextContent(
            type="text",
            text=f"❌ No Robinhood credentials found\n\n"
                 f"Missing: {', '.join(missing)}\n\n"
                 f"Please set these in your .env file:\n"
                 f"ROBINHOOD_USERNAME=your_email@example.com\n"
                 f"ROBINHOOD_PASSWORD=your_password\n\n"
                 f"Once set, I can help you login to Robinhood."
        )
    
    logger.info(f"Auto-login initiated for user: {username}")
    
    try:
        # Try to login without MFA to trigger SMS
        # This will fail but should trigger Robinhood to send SMS
        try:
            rh.login(username=username, password=password, store_session=False)
        except Exception:
            # Expected to fail - this triggers the SMS
            pass
            
        return types.TextContent(
            type="text",
            text=f"🔐 Robinhood Login Initiated\n"
                 f"User: {username}\n\n"
                 f"📱 An SMS with a 6-digit verification code has been sent to your phone.\n\n"
                 f"Please provide the 6-digit MFA code to complete your login."
        )
            
    except Exception as e:
        logger.error(f"Error during auto-login for {username}: {e!s}")
        return types.TextContent(
            type="text", 
            text=f"❌ Login initiation failed: {e!s}\n\n"
                 f"This could be due to:\n"
                 f"• Invalid credentials in .env file\n"
                 f"• Network connectivity issues\n" 
                 f"• Robinhood API issues\n\n"
                 f"Please check your credentials and try again."
        )


async def pass_through_mfa(mfa_code: str) -> types.TextContent:
    """
    Complete Robinhood login using environment credentials and user-provided MFA.
    
    Use this after calling request_mfa() and receiving the SMS code.
    
    Args:
        mfa_code: 6-digit MFA code received via SMS from Robinhood
        
    Returns:
        TextContent: Login status message
    """
    # Get credentials from environment
    username = os.getenv("ROBINHOOD_USERNAME")
    password = os.getenv("ROBINHOOD_PASSWORD")
    
    # Check if credentials are available
    if not username:
        logger.warning("ROBINHOOD_USERNAME not found in environment")
        return types.TextContent(
            type="text",
            text="❌ Missing credentials: Please set ROBINHOOD_USERNAME in your .env file\n"
                 "Example: ROBINHOOD_USERNAME=your_email@example.com"
        )
    
    if not password:
        logger.warning("ROBINHOOD_PASSWORD not found in environment")
        return types.TextContent(
            type="text", 
            text="❌ Missing credentials: Please set ROBINHOOD_PASSWORD in your .env file\n"
                 "Example: ROBINHOOD_PASSWORD=your_password"
        )
    
    logger.info(f"Attempting login for user: {username}")
    
    try:
        # Attempt login with robin-stocks using environment credentials and provided MFA
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
                text=f"✅ Successfully logged into Robinhood\n"
                     f"User: {username}\n"
                     f"Session expires in 24 hours\n"
                     f"You can now use other Robinhood tools."
            )
        else:
            logger.error(f"Login failed for user: {username}")
            return types.TextContent(
                type="text",
                text="❌ Login failed: Invalid MFA code or authentication error\n"
                     "Please check that:\n"
                     "• Your MFA code is correct (6 digits from SMS)\n"
                     "• Your environment credentials are correct\n"
                     "• The MFA code hasn't expired (they expire quickly)"
            )
            
    except Exception as e:
        logger.error(f"Login error for {username}: {e!s}")
        return types.TextContent(
            type="text", 
            text=f"❌ Login error: {e!s}\n"
                 "This could be due to:\n"
                 "• Network connectivity issues\n"
                 "• Invalid credentials in environment\n" 
                 "• Robinhood API issues"
        )


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
