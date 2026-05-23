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

        expiration_data = await execute_broker_request(_get_option_chain, retry_safe=True)

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


_CONTRACT_TYPE_MAP = {
    "call": "CALL",
    "put": "PUT",
    "all": "ALL",
}

_OPEN_ORDER_STATUSES = {
    "WORKING",
    "PENDING_ACTIVATION",
    "QUEUED",
    "ACCEPTED",
    "AWAITING_CONDITION",
    "AWAITING_MANUAL_REVIEW",
    "AWAITING_PARENT_ORDER",
}


_CALL_PUT_ONLY = ("call", "put")


def _resolve_contract_type(option_type: str | None) -> Any:
    """Resolve a string option type to a schwab-py ContractType enum value."""
    if option_type is None:
        return None
    key = option_type.lower()
    if key not in _CONTRACT_TYPE_MAP:
        return None
    enum_name = _CONTRACT_TYPE_MAP[key]
    return getattr(Client.Options.ContractType, enum_name, None)


def _resolve_call_put_only(option_type: str | None) -> Any:
    """Resolve option_type to a ContractType enum, accepting only 'call' or 'put'."""
    if option_type is None:
        return None
    key = option_type.lower()
    if key not in _CALL_PUT_ONLY:
        return None
    return _resolve_contract_type(key)


def _flatten_chain_map(chain_map: dict[str, Any], put_call: str) -> list[dict[str, Any]]:
    """Flatten a Schwab callExpDateMap/putExpDateMap into a list of contracts."""
    contracts: list[dict[str, Any]] = []
    if not isinstance(chain_map, dict):
        return contracts
    for exp_key, strikes in chain_map.items():
        if not isinstance(strikes, dict):
            continue
        # Schwab returns expiration keys as "YYYY-MM-DD:DTE"; strip suffix
        expiration = exp_key.split(":", 1)[0]
        for strike_key, entries in strikes.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                contract = dict(entry)
                contract.setdefault("expiration", expiration)
                contract.setdefault("strike", _safe_float(strike_key))
                contract.setdefault("putCall", put_call)
                contracts.append(contract)
    return contracts


def _safe_float(value: Any) -> float | None:
    """Convert a value to float, returning None on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _strikes_match(actual: Any, requested: float) -> bool:
    """Compare a chain-map strike key against a requested float strike."""
    candidate = _safe_float(actual)
    if candidate is None:
        return False
    return abs(candidate - requested) < 1e-6


def _find_contract_for_expiration(
    chain_map: dict[str, Any],
    expiration: str,
    strike: float,
    put_call: str,
) -> dict[str, Any] | None:
    """Find the first contract entry matching an expiration prefix and strike."""
    if not isinstance(chain_map, dict):
        return None
    for exp_key, strikes in chain_map.items():
        if not exp_key.startswith(expiration):
            continue
        if not isinstance(strikes, dict):
            continue
        for strike_key, entries in strikes.items():
            if not _strikes_match(strike_key, strike):
                continue
            if not isinstance(entries, list) or not entries:
                continue
            first = entries[0]
            if not isinstance(first, dict):
                continue
            contract = dict(first)
            contract.setdefault("expiration", exp_key.split(":", 1)[0])
            contract.setdefault("strike", _safe_float(strike_key))
            contract.setdefault("putCall", put_call)
            return contract
    return None


def _order_has_option_leg(order: dict[str, Any]) -> bool:
    """Return True when an order contains at least one OPTION leg.

    Checks both ``orderLegType`` (older shape) and ``instrument.assetType``
    (current shape) since the Schwab API exposes both.
    """
    legs = order.get("orderLegCollection")
    if not isinstance(legs, list):
        return False
    for leg in legs:
        if not isinstance(leg, dict):
            continue
        if leg.get("orderLegType") == "OPTION":
            return True
        instrument = leg.get("instrument")
        if isinstance(instrument, dict) and instrument.get("assetType") == "OPTION":
            return True
    return False


@handle_schwab_errors
async def schwab_find_tradable_options(
    symbol: str,
    expiration_date: str | None = None,
    option_type: str | None = None,
    strike: float | None = None,
) -> dict[str, Any]:
    """Find tradable option contracts filtered by expiration, type, and strike.

    Args:
        symbol: Underlying stock symbol.
        expiration_date: Optional expiration date (YYYY-MM-DD) to filter by.
        option_type: Optional contract type ('call' or 'put'); ``None`` returns both.
        strike: Optional strike price to filter by.

    Returns:
        Dict with ``options`` (filtered list), ``total_found``, and ``filters``.
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"find tradable options for {symbol}"
    )
    if error:
        return error

    ct = None
    if option_type is not None:
        ct = _resolve_call_put_only(option_type)
        if ct is None:
            return create_error_response(
                ValueError(
                    f"Invalid option_type. Valid options: {list(_CALL_PUT_ONLY)}"
                )
            )

    exp_dt: date | None = None
    if expiration_date is not None:
        try:
            exp_dt = date.fromisoformat(expiration_date)
        except ValueError as exc:
            return create_error_response(exc)

    try:

        def _get_option_chain() -> Any:
            response = broker.client.get_option_chain(
                symbol.upper(),
                contract_type=ct,
                from_date=exp_dt,
                to_date=exp_dt,
            )
            return response.json()

        chain_data = await execute_broker_request(_get_option_chain, retry_safe=True)

        call_map = chain_data.get("callExpDateMap", {}) if isinstance(chain_data, dict) else {}
        put_map = chain_data.get("putExpDateMap", {}) if isinstance(chain_data, dict) else {}

        type_key = option_type.lower() if option_type else None

        options: list[dict[str, Any]] = []
        if type_key != "put":
            options.extend(_flatten_chain_map(call_map, "CALL"))
        if type_key != "call":
            options.extend(_flatten_chain_map(put_map, "PUT"))

        if strike is not None:
            options = [
                contract
                for contract in options
                if _strikes_match(contract.get("strike"), strike)
            ]

        return create_success_response(
            {
                "symbol": symbol.upper(),
                "options": options,
                "total_found": len(options),
                "filters": {
                    "expiration_date": expiration_date,
                    "option_type": option_type.upper() if option_type else None,
                    "strike": strike,
                },
            }
        )

    except Exception as e:
        logger.error(
            f"Error finding tradable Schwab options for {symbol}: {e}"
        )
        return create_error_response(e)


@handle_schwab_errors
async def schwab_get_option_positions_detailed(
    account_hash: str,
) -> dict[str, Any]:
    """Get open option positions enriched with live market quotes.

    Each position is enriched with a ``quote`` dict containing bid/ask/last and
    available greeks looked up via the option chain for the underlying symbol.
    Option chains are fetched at most once per underlying symbol per call.

    Args:
        account_hash: Account hash from get_schwab_account_numbers().

    Returns:
        Dict with ``positions``, ``count``, and ``enrichment_success_rate``.
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

        positions: list[dict[str, Any]] = []
        for position in all_positions:
            instrument = position.get("instrument", {})
            if instrument.get("assetType") != "OPTION":
                continue
            positions.append(
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
                    "quote": {},
                }
            )

        if not positions:
            return create_success_response(
                {
                    "positions": [],
                    "count": 0,
                    "enrichment_success_rate": "0%",
                }
            )

        # Group underlyings so each option chain is fetched once.
        chain_cache: dict[str, dict[str, Any] | None] = {}
        for position in positions:
            underlying = position.get("underlying_symbol")
            if not underlying or underlying in chain_cache:
                continue
            ct = _resolve_contract_type("all")

            def _get_chain(symbol: str = underlying, contract_type: Any = ct) -> Any:
                response = broker.client.get_option_chain(
                    symbol.upper(),
                    contract_type=contract_type,
                )
                return response.json()

            try:
                chain_cache[underlying] = await execute_broker_request(
                    _get_chain, retry_safe=True
                )
            except Exception as chain_error:
                logger.warning(
                    f"Failed to fetch option chain for {underlying}: {chain_error}"
                )
                chain_cache[underlying] = None

        enriched = 0
        for position in positions:
            underlying = position.get("underlying_symbol")
            chain_data = chain_cache.get(underlying) if underlying else None
            if not isinstance(chain_data, dict):
                continue
            strike_price = _safe_float(position.get("strike_price"))
            expiration = position.get("expiration_date")
            option_type = str(position.get("option_type") or "").upper()
            if strike_price is None or not expiration:
                continue
            map_key = (
                "callExpDateMap" if option_type == "CALL" else "putExpDateMap"
            )
            # Schwab expirationDate from positions can include time; strip to date.
            exp_prefix = str(expiration).split("T", 1)[0][:10]
            contract = _find_contract_for_expiration(
                chain_data.get(map_key, {}),
                exp_prefix,
                strike_price,
                option_type,
            )
            if contract is None:
                continue
            position["quote"] = {
                "bid": contract.get("bid"),
                "ask": contract.get("ask"),
                "last": contract.get("last"),
                "mark": contract.get("mark"),
                "delta": contract.get("delta"),
                "gamma": contract.get("gamma"),
                "theta": contract.get("theta"),
                "vega": contract.get("vega"),
                "volatility": contract.get("volatility"),
            }
            enriched += 1

        rate = round((enriched / len(positions)) * 100)

        return create_success_response(
            {
                "positions": positions,
                "count": len(positions),
                "enrichment_success_rate": f"{rate}%",
            }
        )

    except Exception as e:
        logger.error(f"Error getting detailed Schwab option positions: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_get_option_quote(
    symbol: str,
    expiration_date: str,
    strike: float,
    option_type: str,
) -> dict[str, Any]:
    """Get a quote for a single option contract.

    Args:
        symbol: Underlying stock symbol.
        expiration_date: Contract expiration (YYYY-MM-DD).
        strike: Strike price.
        option_type: 'call' or 'put'.

    Returns:
        Dict with the contract data or an error if the contract is not found.
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get option quote for {symbol}"
    )
    if error:
        return error

    ct = _resolve_call_put_only(option_type)
    if ct is None:
        return create_error_response(
            ValueError(
                f"Invalid option_type. Valid options: {list(_CALL_PUT_ONLY)}"
            )
        )

    try:
        exp_dt = date.fromisoformat(expiration_date)
    except ValueError as exc:
        return create_error_response(exc)

    try:

        def _get_option_chain() -> Any:
            response = broker.client.get_option_chain(
                symbol.upper(),
                contract_type=ct,
                from_date=exp_dt,
                to_date=exp_dt,
            )
            return response.json()

        chain_data = await execute_broker_request(_get_option_chain, retry_safe=True)

        put_call = option_type.upper()
        map_key = "callExpDateMap" if put_call == "CALL" else "putExpDateMap"
        chain_map = chain_data.get(map_key, {}) if isinstance(chain_data, dict) else {}

        contract = _find_contract_for_expiration(
            chain_map, expiration_date, strike, put_call
        )
        if contract is None:
            return create_error_response(
                ValueError(
                    f"No {put_call} contract found for {symbol.upper()} "
                    f"{expiration_date} @ {strike}"
                )
            )

        return create_success_response(contract)

    except Exception as e:
        logger.error(f"Error getting Schwab option quote for {symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_get_option_orders(
    account_hash: str,
    max_results: int = 50,
    status: str | None = None,
) -> dict[str, Any]:
    """Get orders filtered to option-legged orders.

    Args:
        account_hash: Account hash from get_schwab_account_numbers().
        max_results: Maximum number of orders to fetch from the broker.
        status: Optional order status filter (e.g. 'FILLED', 'WORKING').

    Returns:
        Dict with ``orders`` (list) and ``count``.
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

        if not isinstance(orders_data, list):
            return create_error_response(
                ValueError("Unexpected orders payload (not a list)")
            )

        filtered: list[dict[str, Any]] = []
        for order in orders_data:
            if not isinstance(order, dict):
                continue
            if not _order_has_option_leg(order):
                continue
            if status is not None and order.get("status") != status:
                continue
            filtered.append(order)

        return create_success_response(
            {
                "orders": filtered,
                "count": len(filtered),
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab option orders: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_get_open_option_orders(
    account_hash: str,
    max_results: int = 50,
) -> dict[str, Any]:
    """Get open (working/pending) option-legged orders.

    Args:
        account_hash: Account hash from get_schwab_account_numbers().
        max_results: Maximum number of orders to fetch from the broker.

    Returns:
        Dict with ``orders`` and ``count``.
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

        if not isinstance(orders_data, list):
            return create_error_response(
                ValueError("Unexpected orders payload (not a list)")
            )

        filtered: list[dict[str, Any]] = []
        for order in orders_data:
            if not isinstance(order, dict):
                continue
            if not _order_has_option_leg(order):
                continue
            if order.get("status") not in _OPEN_ORDER_STATUSES:
                continue
            filtered.append(order)

        return create_success_response(
            {
                "orders": filtered,
                "count": len(filtered),
            }
        )

    except Exception as e:
        logger.error(f"Error getting open Schwab option orders: {e}")
        return create_error_response(e)
