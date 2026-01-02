"""Schwab options MCP tools using schwab-py library."""

import asyncio
from datetime import date
from typing import Any

from open_stocks_mcp.brokers.auth_coordinator import get_authenticated_broker_or_error
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_success_response,
    handle_schwab_errors,
)


@handle_schwab_errors
async def get_schwab_option_chain(
    symbol: str,
    contract_type: str | None = None,
    strike_count: int | None = None,
    include_underlying_quote: bool = True,
) -> dict[str, Any]:
    """Get option chain for a symbol.

    Args:
        symbol: Stock ticker symbol
        contract_type: Type of contracts ('CALL', 'PUT', 'ALL')
        strike_count: Number of strikes above/below at-the-money price
        include_underlying_quote: Whether to include underlying quote

    Returns:
        Dict with option chain data
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get option chain for {symbol}"
    )
    if error:
        return error

    try:
        # Import option types
        from schwab.client import Client

        # Map contract type string to enum
        contract_type_map = {
            "call": Client.Options.ContractType.CALL,
            "put": Client.Options.ContractType.PUT,
            "all": Client.Options.ContractType.ALL,
        }

        ct = None
        if contract_type:
            ct = contract_type_map.get(contract_type.lower())
            if not ct:
                return create_error_response(
                    ValueError(
                        f"Invalid contract_type. Valid options: {list(contract_type_map.keys())}"
                    )
                )

        def _get_option_chain() -> Any:
            response = broker.client.get_option_chain(
                symbol.upper(),
                contract_type=ct,
                strike_count=strike_count,
                include_underlying_quote=include_underlying_quote,
            )
            return response.json()

        chain_data = await asyncio.to_thread(_get_option_chain)

        return create_success_response(chain_data)

    except Exception as e:
        logger.error(f"Error getting Schwab option chain for {symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_option_chain_by_expiration(
    symbol: str,
    from_date: str | None = None,
    to_date: str | None = None,
    contract_type: str | None = None,
) -> dict[str, Any]:
    """Get option chain filtered by expiration dates.

    Args:
        symbol: Stock ticker symbol
        from_date: Only return expirations after this date (YYYY-MM-DD)
        to_date: Only return expirations before this date (YYYY-MM-DD)
        contract_type: Type of contracts ('CALL', 'PUT', 'ALL')

    Returns:
        Dict with filtered option chain data
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get option chain for {symbol}"
    )
    if error:
        return error

    try:
        # Import option types
        from schwab.client import Client

        # Map contract type string to enum
        contract_type_map = {
            "call": Client.Options.ContractType.CALL,
            "put": Client.Options.ContractType.PUT,
            "all": Client.Options.ContractType.ALL,
        }

        ct = None
        if contract_type:
            ct = contract_type_map.get(contract_type.lower())

        # Parse dates
        from_dt = None
        to_dt = None
        if from_date:
            from_dt = date.fromisoformat(from_date)
        if to_date:
            to_dt = date.fromisoformat(to_date)

        def _get_option_chain() -> Any:
            response = broker.client.get_option_chain(
                symbol.upper(),
                contract_type=ct,
                from_date=from_dt,
                to_date=to_dt,
                include_underlying_quote=True,
            )
            return response.json()

        chain_data = await asyncio.to_thread(_get_option_chain)

        return create_success_response(chain_data)

    except Exception as e:
        logger.error(f"Error getting Schwab option chain for {symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_option_expirations(symbol: str) -> dict[str, Any]:
    """Get option expiration dates for a symbol.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dict with list of expiration dates
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get option expirations for {symbol}"
    )
    if error:
        return error

    try:

        def _get_option_chain() -> Any:
            response = broker.client.get_option_expiration_chain(symbol.upper())
            return response.json()

        expiration_data = await asyncio.to_thread(_get_option_chain)

        # Extract expiration dates
        expirations = expiration_data.get("expirationList", [])

        return create_success_response(
            {
                "symbol": symbol.upper(),
                "expirations": expirations,
                "count": len(expirations),
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab option expirations for {symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_options_positions(account_hash: str) -> dict[str, Any]:
    """Get current options positions for an account.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()

    Returns:
        Dict with options positions
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get options positions for {account_hash}"
    )
    if error:
        return error

    try:
        # Import client
        from schwab.client import Client

        def _get_account() -> Any:
            response = broker.client.get_account(
                account_hash, fields=Client.Account.Fields.POSITIONS
            )
            return response.json()

        account_data = await asyncio.to_thread(_get_account)

        # Extract options positions
        securities_account = account_data.get("securitiesAccount", {})
        all_positions = securities_account.get("positions", [])

        # Filter for options
        options_positions = []
        for position in all_positions:
            instrument = position.get("instrument", {})
            asset_type = instrument.get("assetType")

            if asset_type == "OPTION":
                options_positions.append(
                    {
                        "symbol": instrument.get("symbol"),
                        "underlying_symbol": instrument.get("underlyingSymbol"),
                        "option_type": instrument.get("putCall"),
                        "strike_price": instrument.get("strikePrice"),
                        "expiration_date": instrument.get("expirationDate"),
                        "quantity": position.get("longQuantity", 0)
                        + position.get("shortQuantity", 0),
                        "average_price": position.get("averagePrice"),
                        "market_value": position.get("marketValue"),
                        "current_day_pl": position.get("currentDayProfitLoss"),
                    }
                )

        return create_success_response(
            {
                "positions": options_positions,
                "count": len(options_positions),
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab options positions: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_option_buy_to_open(
    account_hash: str,
    symbol: str,
    quantity: int,
    option_type: str,
    strike: float,
    expiration: str,
) -> dict[str, Any]:
    """Buy to open an option position (simplified).

    Note: For complex option orders, use the full order builder.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        symbol: Underlying stock symbol
        quantity: Number of contracts
        option_type: 'CALL' or 'PUT'
        strike: Strike price
        expiration: Expiration date (YYYY-MM-DD)

    Returns:
        Dict with order placement result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"buy {option_type} option for {symbol}"
    )
    if error:
        return error

    try:
        # Import order templates
        from schwab.orders.options import option_buy_to_open_market

        # Create option symbol (simplified - may need adjustment for Schwab format)
        option_symbol = (
            f"{symbol.upper()}_{expiration}_{option_type[0].upper()}{strike}"
        )

        # Create order spec
        order_spec = option_buy_to_open_market(option_symbol, quantity)

        def _place_order() -> Any:
            response = broker.client.place_order(account_hash, order_spec)
            return response

        response = await asyncio.to_thread(_place_order)

        # Check response status
        if response.status_code in (200, 201):
            location = response.headers.get("Location", "")
            order_id = location.split("/")[-1] if location else None

            return create_success_response(
                {
                    "status": "order_placed",
                    "action": "buy_to_open",
                    "symbol": symbol.upper(),
                    "option_type": option_type.upper(),
                    "strike": strike,
                    "expiration": expiration,
                    "quantity": quantity,
                    "order_id": order_id,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Option order failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error placing Schwab option buy order: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_option_sell_to_close(
    account_hash: str,
    symbol: str,
    quantity: int,
    option_type: str,
    strike: float,
    expiration: str,
) -> dict[str, Any]:
    """Sell to close an option position (simplified).

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        symbol: Underlying stock symbol
        quantity: Number of contracts
        option_type: 'CALL' or 'PUT'
        strike: Strike price
        expiration: Expiration date (YYYY-MM-DD)

    Returns:
        Dict with order placement result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"sell {option_type} option for {symbol}"
    )
    if error:
        return error

    try:
        # Import order templates
        from schwab.orders.options import option_sell_to_close_market

        # Create option symbol (simplified - may need adjustment for Schwab format)
        option_symbol = (
            f"{symbol.upper()}_{expiration}_{option_type[0].upper()}{strike}"
        )

        # Create order spec
        order_spec = option_sell_to_close_market(option_symbol, quantity)

        def _place_order() -> Any:
            response = broker.client.place_order(account_hash, order_spec)
            return response

        response = await asyncio.to_thread(_place_order)

        # Check response status
        if response.status_code in (200, 201):
            location = response.headers.get("Location", "")
            order_id = location.split("/")[-1] if location else None

            return create_success_response(
                {
                    "status": "order_placed",
                    "action": "sell_to_close",
                    "symbol": symbol.upper(),
                    "option_type": option_type.upper(),
                    "strike": strike,
                    "expiration": expiration,
                    "quantity": quantity,
                    "order_id": order_id,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Option order failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error placing Schwab option sell order: {e}")
        return create_error_response(e)
