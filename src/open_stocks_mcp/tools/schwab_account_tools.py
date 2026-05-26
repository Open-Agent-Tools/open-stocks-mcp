"""Schwab account-related MCP tools using schwab-py library."""

import datetime
from typing import Any

from schwab.client import Client

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.broker_utils import (
    execute_broker_request,
    get_authenticated_broker_or_error,
)
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_success_response,
)
from open_stocks_mcp.tools.schwab.error_handling import handle_schwab_errors


@handle_schwab_errors
async def get_schwab_account_numbers() -> dict[str, Any]:
    """Get Schwab account numbers and their hashes.

    Returns mapping of account IDs to account hashes needed for API calls.

    Returns:
        Dict with result containing account number to hash mapping
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", "get account numbers"
    )
    if error:
        return error

    try:
        # Execute in thread pool since schwab-py is synchronous
        def _get_account_numbers() -> Any:
            response = broker.client.get_account_numbers()
            return response.json()

        result = await execute_broker_request(_get_account_numbers, retry_safe=True)

        # Extract account hashes
        accounts = []
        for account in result:
            accounts.append(
                {
                    "account_id": account.get("accountNumber"),
                    "hash_value": account.get("hashValue"),
                }
            )

        return create_success_response(
            {
                "accounts": accounts,
                "count": len(accounts),
            }
        )

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
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get account {account_hash}"
    )
    if error:
        return error

    try:
        # Determine fields to request
        fields = None
        if include_positions:
            fields = Client.Account.Fields.POSITIONS

        # Execute in thread pool
        def _get_account() -> Any:
            response = broker.client.get_account(account_hash, fields=fields)
            return response.json()

        account_data = await execute_broker_request(_get_account, retry_safe=True)

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
    broker, error = await get_authenticated_broker_or_error(
        "schwab", "get all accounts"
    )
    if error:
        return error

    try:
        # Determine fields to request
        fields = None
        if include_positions:
            fields = Client.Account.Fields.POSITIONS

        # Execute in thread pool
        def _get_accounts() -> Any:
            response = broker.client.get_accounts(fields=fields)
            return response.json()

        accounts_data = await execute_broker_request(_get_accounts, retry_safe=True)

        return create_success_response(
            {
                "accounts": accounts_data,
                "count": len(accounts_data) if isinstance(accounts_data, list) else 1,
            }
        )

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
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get portfolio {account_hash}"
    )
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

        account_data = await execute_broker_request(_get_account, retry_safe=True)

        # Extract positions
        securities_account = account_data.get("securitiesAccount", {})
        positions = securities_account.get("positions", [])

        # Format positions
        formatted_positions = []
        for position in positions:
            instrument = position.get("instrument", {})
            formatted_positions.append(
                {
                    "symbol": instrument.get("symbol"),
                    "asset_type": instrument.get("assetType"),
                    "quantity": position.get("longQuantity", 0)
                    + position.get("shortQuantity", 0),
                    "average_price": position.get("averagePrice"),
                    "market_value": position.get("marketValue"),
                    "current_price": position.get("currentDayProfitLoss"),
                }
            )

        return create_success_response(
            {
                "positions": formatted_positions,
                "count": len(formatted_positions),
            }
        )

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
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get balances {account_hash}"
    )
    if error:
        return error

    try:

        def _get_account() -> Any:
            # Get account without positions for faster response
            response = broker.client.get_account(account_hash)
            return response.json()

        account_data = await execute_broker_request(_get_account, retry_safe=True)

        # Extract balances
        securities_account = account_data.get("securitiesAccount", {})
        current_balances = securities_account.get("currentBalances", {})
        initial_balances = securities_account.get("initialBalances", {})

        return create_success_response(
            {
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
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab account balances: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_check_margin_status(account_hash: str) -> dict[str, Any]:
    """Derive Schwab margin-call status from account balance fields."""
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"check margin status {account_hash}"
    )
    if error:
        return error

    try:

        def _get_account() -> Any:
            response = broker.client.get_account(account_hash)
            return response.json()

        account_data = await execute_broker_request(_get_account, retry_safe=True)
        securities_account = account_data.get("securitiesAccount", {})
        current_balances = securities_account.get("currentBalances", {})

        equity = float(current_balances.get("equity", 0.0) or 0.0)
        maintenance_requirement = float(
            current_balances.get("maintenanceRequirement", 0.0) or 0.0
        )
        # Schwab has no direct margin-call endpoint, so infer status from equity vs maintenance requirement.
        margin_call = maintenance_requirement > 0 and equity <= maintenance_requirement
        deficit = max(0.0, maintenance_requirement - equity)

        return create_success_response(
            {
                "account_hash": account_hash,
                "account_type": securities_account.get("type"),
                "equity": equity,
                "maintenance_requirement": maintenance_requirement,
                "margin_call": margin_call,
                "deficit": deficit,
                "status": "success",
            }
        )
    except Exception as e:
        logger.error(f"Error checking Schwab margin status: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_get_margin_interest(
    account_hash: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Get Schwab margin-interest transactions from transaction history."""
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get margin interest {account_hash}"
    )
    if error:
        return error

    try:
        parsed_start_date = (
            datetime.date.fromisoformat(start_date) if start_date else None
        )
        parsed_end_date = datetime.date.fromisoformat(end_date) if end_date else None

        def _get_transactions() -> Any:
            response = broker.client.get_transactions(
                account_hash,
                start_date=parsed_start_date,
                end_date=parsed_end_date,
                transaction_types=[
                    Client.Transactions.TransactionType.DIVIDEND_OR_INTEREST
                ],
            )
            return response.json()

        transactions = await execute_broker_request(_get_transactions, retry_safe=True)
        margin_interest_transactions = [
            txn
            for txn in transactions
            if "MARGIN INTEREST" in str(txn.get("description", "")).upper()
        ]
        total_charges = sum(
            abs(float(txn.get("netAmount", 0.0) or 0.0))
            for txn in margin_interest_transactions
        )

        return create_success_response(
            {
                "interest_charges": margin_interest_transactions,
                "total_charges": total_charges,
                "charges_count": len(margin_interest_transactions),
                "status": "success",
            }
        )
    except Exception as e:
        logger.error(f"Error getting Schwab margin interest: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_user_preferences() -> dict[str, Any]:
    """Get Schwab user preferences including account list and streamer info.

    Consolidates account profile, settings, and user profile data.

    Returns:
        Dict with result containing user preferences
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", "get user preferences"
    )
    if error:
        return error

    try:

        def _get_user_preferences() -> Any:
            response = broker.client.get_user_preferences()
            return response.json()

        result = await execute_broker_request(_get_user_preferences, retry_safe=True)

        return create_success_response({"user_preferences": result})

    except Exception as e:
        logger.error(f"Error getting Schwab user preferences: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_all_account_data() -> dict[str, Any]:
    """Get a complete snapshot of all Schwab accounts and user preferences.

    Aggregates user preferences, account numbers, and all account data with positions.

    Returns:
        Dict with result containing aggregated account snapshot
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", "get all account data"
    )
    if error:
        return error

    try:
        # 1. Get User Preferences
        def _get_prefs() -> Any:
            return broker.client.get_user_preferences().json()

        user_preferences = await execute_broker_request(_get_prefs, retry_safe=True)

        # 2. Get Account Numbers
        def _get_numbers() -> Any:
            return broker.client.get_account_numbers().json()

        account_numbers = await execute_broker_request(_get_numbers, retry_safe=True)

        # 3. Get All Accounts with Positions
        def _get_accounts() -> Any:
            return broker.client.get_accounts(
                fields=Client.Account.Fields.POSITIONS
            ).json()

        accounts_data = await execute_broker_request(_get_accounts, retry_safe=True)

        return create_success_response(
            {
                "user_preferences": user_preferences,
                "account_numbers": account_numbers,
                "accounts": accounts_data,
                "count": len(accounts_data) if isinstance(accounts_data, list) else 1,
            }
        )

    except Exception as e:
        logger.error(f"Error aggregating Schwab account data: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def build_schwab_user_profile() -> dict[str, Any]:
    """Build a normalized Schwab user profile from account and preference data.

    Returns:
        Dict with result containing normalized user profile
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", "build user profile"
    )
    if error:
        return error

    try:
        # Fetch required data
        def _get_prefs() -> Any:
            return broker.client.get_user_preferences().json()

        user_preferences = await execute_broker_request(_get_prefs, retry_safe=True)

        def _get_accounts() -> Any:
            return broker.client.get_accounts(
                fields=Client.Account.Fields.POSITIONS
            ).json()

        accounts_data = await execute_broker_request(_get_accounts, retry_safe=True)

        # Normalize data
        accounts = []
        total_equity = 0.0
        total_cash = 0.0
        total_positions = 0

        for account in accounts_data:
            sec_account = account.get("securitiesAccount", {})
            balances = sec_account.get("currentBalances", {})

            acct_equity = balances.get("liquidationValue", 0.0)
            acct_cash = balances.get("cashBalance", 0.0)
            acct_positions = len(sec_account.get("positions", []))

            total_equity += acct_equity
            total_cash += acct_cash
            total_positions += acct_positions

            accounts.append(
                {
                    "account_number": sec_account.get("accountNumber"),
                    "type": sec_account.get("type"),
                    "equity": acct_equity,
                    "cash": acct_cash,
                    "position_count": acct_positions,
                }
            )

        user_profile = {
            "user_preferences": user_preferences,
            "accounts": accounts,
            "account_count": len(accounts),
            "total_equity": total_equity,
            "total_cash": total_cash,
            "total_positions_count": total_positions,
        }

        return create_success_response({"user_profile": user_profile})

    except Exception as e:
        logger.error(f"Error building Schwab user profile: {e}")
        return create_error_response(e)
