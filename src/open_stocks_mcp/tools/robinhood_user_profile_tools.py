"""
User Profile Tools for Robin Stocks MCP Server.

This module provides comprehensive user profile management tools including:
- Account profile and trading settings
- Basic user information and preferences
- Investment profile and risk assessment
- Security settings and configurations

All functions use Robin Stocks API with proper error handling and async support.
"""

from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    execute_with_retry,
    handle_robin_stocks_errors,
)


@handle_robin_stocks_errors
async def get_account_profile() -> dict[str, Any]:
    """
    Get trading account profile and configuration.

    This function retrieves comprehensive trading account information
    including account limits, settings, and trading configurations.

    Returns:
        Dict containing account profile data:
        {
            "result": {
                "account_profile": {
                    "account_number": "12345678",
                    "day_trade_count": 2,
                    "max_ach_early_access_amount": "1000.00",
                    "cash_management_enabled": true,
                    "option_level": "2",
                    "instant_eligibility": true,
                    "margin_balances": {
                        "day_trade_buying_power": "25000.00",
                        "overnight_buying_power": "12500.00"
                    }
                },
                "status": "success"
            }
        }
    """
    logger.info("Getting account profile")

    # Get account profile
    profile_data = await execute_with_retry(
        func=rh.load_account_profile, func_name="load_account_profile", max_retries=3
    )

    if not profile_data:
        logger.warning("No account profile data found")
        return {
            "result": {
                "account_profile": {},
                "error": "No account profile data found",
                "status": "no_data",
            }
        }

    logger.info("Successfully retrieved account profile")

    return {"result": {"account_profile": profile_data, "status": "success"}}


@handle_robin_stocks_errors
async def get_basic_profile() -> dict[str, Any]:
    """
    Get basic user profile information.

    This function retrieves basic user information including
    personal details and account preferences.

    Returns:
        Dict containing basic profile data:
        {
            "result": {
                "basic_profile": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@example.com",
                    "phone_number": "+1234567890",
                    "date_of_birth": "1990-01-01",
                    "address": {
                        "city": "New York",
                        "state": "NY",
                        "zipcode": "10001"
                    },
                    "employment": {
                        "employment_status": "employed",
                        "employer": "Tech Corp",
                        "position": "Software Engineer"
                    }
                },
                "status": "success"
            }
        }
    """
    logger.info("Getting basic profile")

    # Get basic profile
    profile_data = await execute_with_retry(
        func=rh.load_basic_profile, func_name="load_basic_profile", max_retries=3
    )

    if not profile_data:
        logger.warning("No basic profile data found")
        return {
            "result": {
                "basic_profile": {},
                "error": "No basic profile data found",
                "status": "no_data",
            }
        }

    logger.info("Successfully retrieved basic profile")

    return {"result": {"basic_profile": profile_data, "status": "success"}}


@handle_robin_stocks_errors
async def get_investment_profile() -> dict[str, Any]:
    """
    Get investment profile and risk assessment.

    This function retrieves the user's investment profile including
    risk tolerance, investment experience, and trading objectives.

    Returns:
        Dict containing investment profile data:
        {
            "result": {
                "investment_profile": {
                    "risk_tolerance": "moderate",
                    "investment_experience": "some_experience",
                    "investment_objective": "growth",
                    "time_horizon": "long_term",
                    "liquidity_needs": "low",
                    "annual_income": "50000-100000",
                    "net_worth": "100000-250000",
                    "investment_experience_stocks": "some_experience",
                    "investment_experience_options": "no_experience",
                    "option_trading_experience": "none",
                    "professional_trader": false
                },
                "status": "success"
            }
        }
    """
    logger.info("Getting investment profile")

    # Get investment profile
    profile_data = await execute_with_retry(
        func=rh.load_investment_profile,
        func_name="load_investment_profile",
        max_retries=3,
    )

    if not profile_data:
        logger.warning("No investment profile data found")
        return {
            "result": {
                "investment_profile": {},
                "error": "No investment profile data found",
                "status": "no_data",
            }
        }

    logger.info("Successfully retrieved investment profile")

    return {"result": {"investment_profile": profile_data, "status": "success"}}


@handle_robin_stocks_errors
async def get_security_profile() -> dict[str, Any]:
    """
    Get security profile and settings.

    This function retrieves security-related settings and configurations
    including authentication methods and security preferences.

    Returns:
        Dict containing security profile data:
        {
            "result": {
                "security_profile": {
                    "sms_enabled": true,
                    "email_enabled": true,
                    "push_notifications": true,
                    "two_factor_enabled": true,
                    "backup_codes_generated": true,
                    "last_login": "2024-01-15T10:30:00Z",
                    "login_attempts": 0,
                    "account_locked": false,
                    "password_reset_required": false
                },
                "status": "success"
            }
        }
    """
    logger.info("Getting security profile")

    # Get security profile
    profile_data = await execute_with_retry(
        func=rh.load_security_profile, func_name="load_security_profile", max_retries=3
    )

    if not profile_data:
        logger.warning("No security profile data found")
        return {
            "result": {
                "security_profile": {},
                "error": "No security profile data found",
                "status": "no_data",
            }
        }

    logger.info("Successfully retrieved security profile")

    return {"result": {"security_profile": profile_data, "status": "success"}}


@handle_robin_stocks_errors
async def get_user_profile() -> dict[str, Any]:
    """
    Get comprehensive user profile information.

    This function retrieves the main user profile which typically includes
    account information, portfolio data, and user settings.

    Returns:
        Dict containing user profile data:
        {
            "result": {
                "user_profile": {
                    "username": "john_doe",
                    "email": "john.doe@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "id": "user_id_here",
                    "created_at": "2020-01-01T00:00:00Z",
                    "email_verified": true,
                    "phone_number": "+1234567890",
                    "profile_name": "John Doe"
                },
                "status": "success"
            }
        }
    """
    logger.info("Getting user profile")

    # Get user profile
    profile_data = await execute_with_retry(
        func=rh.load_user_profile, func_name="load_user_profile", max_retries=3
    )

    if not profile_data:
        logger.warning("No user profile data found")
        return {
            "result": {
                "user_profile": {},
                "error": "No user profile data found",
                "status": "no_data",
            }
        }

    logger.info("Successfully retrieved user profile")

    return {"result": {"user_profile": profile_data, "status": "success"}}


@handle_robin_stocks_errors
async def get_complete_profile() -> dict[str, Any]:
    """
    Get complete user profile combining all profile types.

    This function retrieves and combines data from all profile types
    for a comprehensive view of the user's account and settings.

    Returns:
        Dict containing complete profile data:
        {
            "result": {
                "complete_profile": {
                    "user_info": {...},
                    "basic_profile": {...},
                    "account_profile": {...},
                    "investment_profile": {...},
                    "security_profile": {...}
                },
                "profiles_loaded": 5,
                "status": "success"
            }
        }
    """
    logger.info("Getting complete user profile")

    complete_profile = {}
    profiles_loaded = 0

    try:
        # Get user profile
        user_result = await get_user_profile()
        if user_result["result"]["status"] == "success":
            complete_profile["user_info"] = user_result["result"]["user_profile"]
            profiles_loaded += 1

        # Get basic profile
        basic_result = await get_basic_profile()
        if basic_result["result"]["status"] == "success":
            complete_profile["basic_profile"] = basic_result["result"]["basic_profile"]
            profiles_loaded += 1

        # Get account profile
        account_result = await get_account_profile()
        if account_result["result"]["status"] == "success":
            complete_profile["account_profile"] = account_result["result"][
                "account_profile"
            ]
            profiles_loaded += 1

        # Get investment profile
        investment_result = await get_investment_profile()
        if investment_result["result"]["status"] == "success":
            complete_profile["investment_profile"] = investment_result["result"][
                "investment_profile"
            ]
            profiles_loaded += 1

        # Get security profile
        security_result = await get_security_profile()
        if security_result["result"]["status"] == "success":
            complete_profile["security_profile"] = security_result["result"][
                "security_profile"
            ]
            profiles_loaded += 1

        logger.info(f"Successfully loaded {profiles_loaded} profiles")

        return {
            "result": {
                "complete_profile": complete_profile,
                "profiles_loaded": profiles_loaded,
                "status": "success",
            }
        }

    except Exception as e:
        logger.error(f"Error loading complete profile: {e}")
        return {
            "result": {
                "complete_profile": complete_profile,
                "profiles_loaded": profiles_loaded,
                "error": f"Error loading complete profile: {e!s}",
                "status": "partial_success",
            }
        }


@handle_robin_stocks_errors
async def get_account_settings() -> dict[str, Any]:
    """
    Get account settings and preferences.

    This function retrieves account-specific settings including
    notifications, trading preferences, and feature toggles.

    Returns:
        Dict containing account settings:
        {
            "result": {
                "settings": {
                    "instant_settlement": true,
                    "margin_enabled": true,
                    "options_enabled": true,
                    "crypto_enabled": true,
                    "dividend_reinvestment": false,
                    "email_notifications": true,
                    "push_notifications": true,
                    "sms_notifications": false,
                    "paper_statements": false,
                    "extended_hours_trading": true
                },
                "status": "success"
            }
        }
    """
    logger.info("Getting account settings")

    try:
        # Get account profile which contains most settings
        account_result = await get_account_profile()

        if account_result["result"]["status"] != "success":
            return {
                "result": {
                    "settings": {},
                    "error": "Could not retrieve account settings",
                    "status": "error",
                }
            }

        account_data = account_result["result"]["account_profile"]

        # Extract settings from account data
        settings = {
            "instant_settlement": account_data.get("instant_eligibility", False),
            "margin_enabled": "margin_balances" in account_data,
            "options_enabled": account_data.get("option_level", "0") != "0",
            "crypto_enabled": account_data.get("crypto_enabled", False),
            "dividend_reinvestment": account_data.get("dividend_reinvestment", False),
            "extended_hours_trading": account_data.get("extended_hours_trading", False),
            "day_trade_count": account_data.get("day_trade_count", 0),
            "cash_management_enabled": account_data.get(
                "cash_management_enabled", False
            ),
            "max_ach_early_access": account_data.get(
                "max_ach_early_access_amount", "0.00"
            ),
        }

        logger.info("Successfully retrieved account settings")

        return {
            "result": {
                "settings": settings,
                "raw_account_data": account_data,
                "status": "success",
            }
        }

    except Exception as e:
        logger.error(f"Error retrieving account settings: {e}")
        return {
            "result": {
                "settings": {},
                "error": f"Error retrieving account settings: {e!s}",
                "status": "error",
            }
        }
