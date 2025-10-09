"""Schwab account-related MCP tools using schwab-py library."""

import asyncio
from typing import Any

from open_stocks_mcp.brokers.auth_coordinator import get_authenticated_broker_or_error
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_success_response,
    handle_schwab_errors,
)


@handle_schwab_errors
async def get_schwab_account_numbers() -> dict[str, Any]:
    """Get Schwab account numbers and their hashes.

    Returns mapping of account IDs to account hashes needed for API calls.

    Returns:
        Dict with result containing account number to hash mapping
    """
    broker, error = await get_authenticated_broker_or_error("schwab", "get account numbers")
    if error:
        return error

    try:
        # Execute in thread pool since schwab-py is synchronous
        def _get_account_numbers() -> Any:
            response = broker.client.get_account_numbers()
            return response.json()

        result = await asyncio.to_thread(_get_account_numbers)

        # Extract account hashes
        accounts = []
        for account in result:
            accounts.append({
                "account_id": account.get("accountNumber"),
                "hash_value": account.get("hashValue"),
            })

        return create_success_response({
            "accounts": accounts,
            "count": len(accounts),
        })

    except Exception as e:
        logger.error(f"Error getting Schwab account numbers: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_account(
    account_hash: str, include_positions: bool = True
) -> dict[str, Any]:
    """Get Schwab account details including balances and positions.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        include_positions: Whether to include positions (default: True)

    Returns:
        Dict with account details, balances, and positions
    """
    broker, error = await get_authenticated_broker_or_error("schwab", f"get account {account_hash}")
    if error:
        return error

    try:
        # Import here to avoid dependency issues
        from schwab.client import Client

        # Determine fields to request
        fields = None
        if include_positions:
            fields = Client.Account.Fields.POSITIONS

        # Execute in thread pool
        def _get_account() -> Any:
            response = broker.client.get_account(account_hash, fields=fields)
            return response.json()

        account_data = await asyncio.to_thread(_get_account)

        return create_success_response(account_data)

    except Exception as e:
        logger.error(f"Error getting Schwab account: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_accounts(include_positions: bool = True) -> dict[str, Any]:
    """Get all Schwab linked accounts with balances and positions.

    Args:
        include_positions: Whether to include positions (default: True)

    Returns:
        Dict with all accounts, balances, and positions
    """
    broker, error = await get_authenticated_broker_or_error("schwab", "get all accounts")
    if error:
        return error

    try:
        # Import here to avoid dependency issues
        from schwab.client import Client

        # Determine fields to request
        fields = None
        if include_positions:
            fields = Client.Account.Fields.POSITIONS

        # Execute in thread pool
        def _get_accounts() -> Any:
            response = broker.client.get_accounts(fields=fields)
            return response.json()

        accounts_data = await asyncio.to_thread(_get_accounts)

        return create_success_response({
            "accounts": accounts_data,
            "count": len(accounts_data) if isinstance(accounts_data, list) else 1,
        })

    except Exception as e:
        logger.error(f"Error getting Schwab accounts: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_portfolio(account_hash: str) -> dict[str, Any]:
    """Get Schwab portfolio positions for a specific account.

    Convenience function that returns just the positions from an account.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()

    Returns:
        Dict with portfolio positions
    """
    broker, error = await get_authenticated_broker_or_error("schwab", f"get portfolio {account_hash}")
    if error:
        return error

    try:
        # Get account with positions
        from schwab.client import Client

        def _get_account() -> Any:
            response = broker.client.get_account(
                account_hash, fields=Client.Account.Fields.POSITIONS
            )
            return response.json()

        account_data = await asyncio.to_thread(_get_account)

        # Extract positions
        securities_account = account_data.get("securitiesAccount", {})
        positions = securities_account.get("positions", [])

        # Format positions
        formatted_positions = []
        for position in positions:
            instrument = position.get("instrument", {})
            formatted_positions.append({
                "symbol": instrument.get("symbol"),
                "asset_type": instrument.get("assetType"),
                "quantity": position.get("longQuantity", 0) + position.get("shortQuantity", 0),
                "average_price": position.get("averagePrice"),
                "market_value": position.get("marketValue"),
                "current_price": position.get("currentDayProfitLoss"),
            })

        return create_success_response({
            "positions": formatted_positions,
            "count": len(formatted_positions),
        })

    except Exception as e:
        logger.error(f"Error getting Schwab portfolio: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_account_balances(account_hash: str) -> dict[str, Any]:
    """Get account balances for a Schwab account.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()

    Returns:
        Dict with account balances and buying power
    """
    broker, error = await get_authenticated_broker_or_error("schwab", f"get balances {account_hash}")
    if error:
        return error

    try:
        def _get_account() -> Any:
            # Get account without positions for faster response
            response = broker.client.get_account(account_hash)
            return response.json()

        account_data = await asyncio.to_thread(_get_account)

        # Extract balances
        securities_account = account_data.get("securitiesAccount", {})
        current_balances = securities_account.get("currentBalances", {})
        initial_balances = securities_account.get("initialBalances", {})

        return create_success_response({
            "account_id": securities_account.get("accountNumber"),
            "account_type": securities_account.get("type"),
            "current_balances": {
                "cash_balance": current_balances.get("cashBalance"),
                "market_value": current_balances.get("liquidationValue"),
                "buying_power": current_balances.get("buyingPower"),
                "available_funds": current_balances.get("availableFunds"),
            },
            "initial_balances": {
                "cash_balance": initial_balances.get("cashBalance"),
                "account_value": initial_balances.get("accountValue"),
            },
        })

    except Exception as e:
        logger.error(f"Error getting Schwab account balances: {e}")
        return create_error_response(e)
