"""Schwab options MCP tools using schwab-py library."""

from datetime import date
from typing import Any

from schwab.client import Client
from schwab.orders.options import option_buy_to_open_market, option_sell_to_close_market

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.broker_utils import (
    execute_broker_request,
    get_authenticated_broker_or_error,
)
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_success_response,
    handle_schwab_errors,
)

_OPEN_OPTION_STATUSES = frozenset(
    {
        "WORKING",
        "PENDING_ACTIVATION",
        "QUEUED",
        "ACCEPTED",
        "AWAITING_CONDITION",
        "AWAITING_MANUAL_REVIEW",
        "AWAITING_PARENT_ORDER",
    }
)


def _has_option_leg(order: dict[str, Any]) -> bool:
    """Return True when any leg of the order is an option instrument."""
    legs = order.get("orderLegCollection", [])
    return any(
        leg.get("orderLegType") == "OPTION"
        or leg.get("instrument", {}).get("assetType") == "OPTION"
        for leg in legs
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

        chain_data = await execute_broker_request(_get_option_chain, retry_safe=True)

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

        chain_data = await execute_broker_request(_get_option_chain, retry_safe=True)

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

        expiration_data = await execute_broker_request(
            _get_option_chain, retry_safe=True
        )

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

        def _get_account() -> Any:
            response = broker.client.get_account(
                account_hash, fields=Client.Account.Fields.POSITIONS
            )
            return response.json()

        account_data = await execute_broker_request(_get_account, retry_safe=True)

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
async def get_schwab_option_positions_detailed(
    account_hash: str,
) -> dict[str, Any]:
    """Get options positions enriched with live quote data from option chains.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()

    Returns:
        Dict with enriched options positions including bid/ask/last/mark/greeks
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get detailed option positions for {account_hash}"
    )
    if error:
        return error

    try:

        def _get_account() -> Any:
            response = broker.client.get_account(
                account_hash, fields=Client.Account.Fields.POSITIONS
            )
            return response.json()

        account_data = await execute_broker_request(_get_account, retry_safe=True)

        securities_account = account_data.get("securitiesAccount", {})
        all_positions = securities_account.get("positions", [])

        option_positions = [
            p
            for p in all_positions
            if p.get("instrument", {}).get("assetType") == "OPTION"
        ]

        if not option_positions:
            return create_success_response(
                {"positions": [], "count": 0, "enrichment_success_rate": "0%"}
            )

        underlyings = {
            p["instrument"]["underlyingSymbol"]
            for p in option_positions
            if p.get("instrument", {}).get("underlyingSymbol")
        }

        chain_cache: dict[str, Any] = {}
        for underlying in underlyings:
            try:

                def _get_chain(sym: str = underlying) -> Any:
                    response = broker.client.get_option_chain(
                        sym.upper(), include_underlying_quote=False
                    )
                    return response.json()

                chain_cache[underlying] = await execute_broker_request(
                    _get_chain, retry_safe=True
                )
            except Exception:
                logger.warning(f"Failed to fetch option chain for {underlying}")

        enriched: list[dict[str, Any]] = []
        enriched_count = 0

        for position in option_positions:
            instrument = position.get("instrument", {})
            pos_symbol = instrument.get("symbol", "")
            underlying = instrument.get("underlyingSymbol", "")
            put_call = instrument.get("putCall", "")

            pos_dict: dict[str, Any] = {
                "symbol": pos_symbol,
                "underlying_symbol": underlying,
                "option_type": put_call,
                "strike_price": instrument.get("strikePrice"),
                "expiration_date": instrument.get("expirationDate"),
                "quantity": position.get("longQuantity", 0)
                + position.get("shortQuantity", 0),
                "average_price": position.get("averagePrice"),
                "market_value": position.get("marketValue"),
                "current_day_pl": position.get("currentDayProfitLoss"),
                "quote": None,
            }

            chain = chain_cache.get(underlying)
            if chain:
                exp_map_key = (
                    "callExpDateMap" if put_call == "CALL" else "putExpDateMap"
                )
                exp_map = chain.get(exp_map_key, {})
                matched = False
                for _exp_date, strikes in exp_map.items():
                    for _strike, contracts in strikes.items():
                        for contract in contracts:
                            if contract.get("symbol") == pos_symbol:
                                pos_dict["quote"] = {
                                    "bid": contract.get("bid"),
                                    "ask": contract.get("ask"),
                                    "last": contract.get("last"),
                                    "mark": contract.get("mark"),
                                    "greeks": contract.get("greeks"),
                                }
                                enriched_count += 1
                                matched = True
                                break
                        if matched:
                            break
                    if matched:
                        break

            enriched.append(pos_dict)

        total = len(enriched)
        rate = f"{round(enriched_count / total * 100)}%" if total > 0 else "0%"

        return create_success_response(
            {
                "positions": enriched,
                "count": total,
                "enrichment_success_rate": rate,
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab detailed option positions: {e}")
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
        # Create option symbol (simplified - may need adjustment for Schwab format)
        option_symbol = (
            f"{symbol.upper()}_{expiration}_{option_type[0].upper()}{strike}"
        )

        # Create order spec
        order_spec = option_buy_to_open_market(option_symbol, quantity)

        def _place_order() -> Any:
            response = broker.client.place_order(account_hash, order_spec)
            return response

        response = await execute_broker_request(_place_order, retry_safe=False)

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
async def schwab_find_tradable_options(
    symbol: str,
    expiration_date: str | None = None,
    option_type: str | None = None,
    strike: float | None = None,
) -> dict[str, Any]:
    """Find tradable option contracts filtered by expiration, type, and strike.

    Args:
        symbol: Stock ticker symbol
        expiration_date: Filter to contracts expiring on this date (YYYY-MM-DD)
        option_type: 'call' or 'put'
        strike: Strike price to filter on

    Returns:
        Dict with matching options list, total_found count, and applied filters
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"find tradable options for {symbol}"
    )
    if error:
        return error

    try:
        valid_option_types = {"call", "put"}
        if option_type is not None and option_type.lower() not in valid_option_types:
            return create_error_response(
                ValueError(
                    f"Invalid option_type '{option_type}'. Valid options: {sorted(valid_option_types)}"
                )
            )

        # Map to Schwab SDK contract type enum so the API call is scoped when possible
        contract_type_map = {
            "call": Client.Options.ContractType.CALL,
            "put": Client.Options.ContractType.PUT,
        }
        ct = contract_type_map.get(option_type.lower()) if option_type else None

        expiry_dt = None
        if expiration_date:
            expiry_dt = date.fromisoformat(expiration_date)

        def _get_option_chain() -> Any:
            response = broker.client.get_option_chain(
                symbol.upper(),
                contract_type=ct,
                from_date=expiry_dt,
                to_date=expiry_dt,
            )
            return response.json()

        chain_data = await execute_broker_request(_get_option_chain, retry_safe=True)

        # Flatten callExpDateMap and putExpDateMap into a single list of contracts
        options: list[dict[str, Any]] = []

        maps_to_scan: list[tuple[str, dict[str, Any]]] = []
        if option_type is None or option_type.lower() == "call":
            maps_to_scan.append(("call", chain_data.get("callExpDateMap", {})))
        if option_type is None or option_type.lower() == "put":
            maps_to_scan.append(("put", chain_data.get("putExpDateMap", {})))

        for _side, exp_map in maps_to_scan:
            for exp_key, strikes_map in exp_map.items():
                # Schwab keys may carry a DTE suffix: "YYYY-MM-DD:DTE"
                exp_prefix = exp_key.split(":")[0]
                if expiration_date and exp_prefix != expiration_date:
                    continue

                for strike_key, contracts in strikes_map.items():
                    if strike is not None and float(strike_key) != strike:
                        continue
                    options.extend(contracts)

        return create_success_response(
            {
                "options": options,
                "total_found": len(options),
                "filters": {
                    "symbol": symbol.upper(),
                    "expiration_date": expiration_date,
                    "option_type": option_type,
                    "strike": strike,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error finding tradable options for {symbol}: {e}")
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
        # Create option symbol (simplified - may need adjustment for Schwab format)
        option_symbol = (
            f"{symbol.upper()}_{expiration}_{option_type[0].upper()}{strike}"
        )

        # Create order spec
        order_spec = option_sell_to_close_market(option_symbol, quantity)

        def _place_order() -> Any:
            response = broker.client.place_order(account_hash, order_spec)
            return response

        response = await execute_broker_request(_place_order, retry_safe=False)

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


@handle_schwab_errors
async def schwab_get_open_option_orders(
    account_hash: str, max_results: int = 50
) -> dict[str, Any]:
    """Get open option orders for a Schwab account.

    Filters to orders that have at least one option leg and are in a working/open
    status set (WORKING, PENDING_ACTIVATION, QUEUED, ACCEPTED, AWAITING_CONDITION,
    AWAITING_MANUAL_REVIEW, AWAITING_PARENT_ORDER).

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        max_results: Maximum number of orders to fetch before filtering (default 50)

    Returns:
        Dict with filtered option orders and count
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get open option orders for {account_hash}"
    )
    if error:
        return error

    try:

        def _get_orders() -> Any:
            response = broker.client.get_orders_for_account(
                account_hash, max_results=max_results
            )
            return response.json()

        orders_data = await execute_broker_request(_get_orders, retry_safe=True)
        all_orders = orders_data if isinstance(orders_data, list) else []

        open_option_orders = [
            o
            for o in all_orders
            if _has_option_leg(o) and o.get("status") in _OPEN_OPTION_STATUSES
        ]

        return create_success_response(
            {"orders": open_option_orders, "count": len(open_option_orders)}
        )

    except Exception as e:
        logger.error(f"Error getting Schwab open option orders for {account_hash}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_get_option_orders(
    account_hash: str, max_results: int = 50, status: str | None = None
) -> dict[str, Any]:
    """Get option orders for a Schwab account, optionally filtered by status.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        max_results: Maximum number of orders to fetch before filtering (default 50)
        status: Optional order status filter (e.g. FILLED, WORKING, CANCELED)

    Returns:
        Dict with filtered option orders and count
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get option orders for {account_hash}"
    )
    if error:
        return error

    try:

        def _get_orders() -> Any:
            response = broker.client.get_orders_for_account(
                account_hash, max_results=max_results
            )
            return response.json()

        orders_data = await execute_broker_request(_get_orders, retry_safe=True)
        all_orders = orders_data if isinstance(orders_data, list) else []
        option_orders = [order for order in all_orders if _has_option_leg(order)]
        if status is not None:
            option_orders = [
                order for order in option_orders if order.get("status") == status
            ]

        return create_success_response(
            {"orders": option_orders, "count": len(option_orders)}
        )

    except Exception as e:
        logger.error(f"Error getting Schwab option orders for {account_hash}: {e}")
        return create_error_response(e)
