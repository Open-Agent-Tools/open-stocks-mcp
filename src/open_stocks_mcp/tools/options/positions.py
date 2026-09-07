"""Robinhood options position tools."""

import contextlib
from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.batch_fetch import dedupe_preserving_order, gather_bounded
from open_stocks_mcp.tools.error_handling import (
    execute_with_retry,
    handle_robin_stocks_errors,
)


def _extract_option_id(position: Any) -> str | None:
    """Return the option_id for ``position`` if present, otherwise None.

    Accepts both ``option_id`` directly and a trailing-segment ID parsed from
    the ``option`` URL field (matching the prior inline extraction).
    """
    if not isinstance(position, dict):
        return None
    option_id = position.get("option_id")
    if option_id:
        return str(option_id)
    option_url = position.get("option")
    if option_url and isinstance(option_url, str):
        url_parts = option_url.rstrip("/").split("/")
        return url_parts[-1] if url_parts else None
    return None


async def _resolve_option_instruments(
    option_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Look up option-instrument metadata for each ``option_id`` concurrently."""
    if not option_ids:
        return {}

    results = await gather_bounded(
        [
            execute_with_retry(
                rh.options.get_option_instrument_data_by_id,
                option_id,
                max_retries=2,
            )
            for option_id in option_ids
        ]
    )
    resolved: dict[str, dict[str, Any]] = {}
    for option_id, value in zip(option_ids, results, strict=True):
        if isinstance(value, BaseException):
            logger.warning(f"Failed to fetch option details for {option_id}: {value}")
            continue
        if isinstance(value, dict):
            resolved[option_id] = value
    return resolved


@handle_robin_stocks_errors
async def get_aggregate_positions() -> dict[str, Any]:
    """
    Get all option positions (not actually aggregated).

    Despite the name, this function returns individual option position objects
    from Robin Stocks, not aggregated data. Each position includes detailed
    information about strategy, legs, prices, and clearing data.

    Returns:
        Dict containing array of individual option positions:
        {
            "result": {
                "positions": [
                    {
                        "id": "d97ac32e-45f6-42e9-bc2b-a4cff8c6c488",
                        "chain": "https://api.robinhood.com/options/chains/b905e24f-f046-458c-af25-244dbe46616c/",
                        "account": "https://api.robinhood.com/accounts/894785138/",
                        "account_number": "894785138",
                        "symbol": "F",
                        "strategy": "short_call",
                        "average_open_price": "29.0000",
                        "legs": [
                            {
                                "id": "c77d0bd5-bb53-4b06-a93f-0a281fb5b2bf",
                                "ratio_quantity": 1,
                                "position": "https://api.robinhood.com/options/positions/7dd81e42-0d94-4630-a668-873c38164a1b/",
                                "position_type": "short",
                                "option": "https://api.robinhood.com/options/instruments/845df489-f082-4141-9e39-e6b7654f5f75/",
                                "option_id": "845df489-f082-4141-9e39-e6b7654f5f75",
                                "expiration_date": "2025-09-12",
                                "strike_price": "11.5000",
                                "option_type": "call",
                                "settle_on_open": false
                            }
                        ],
                        "quantity": "1.0000",
                        "intraday_average_open_price": "29.0000",
                        "intraday_quantity": "1",
                        "direction": "credit",
                        "intraday_direction": "credit",
                        "trade_value_multiplier": "100.0000",
                        "created_at": "2025-08-11T13:42:16.553634Z",
                        "updated_at": "2025-08-11T13:42:16.548478Z",
                        "strategy_code": "845df489-f082-4141-9e39-e6b7654f5f75_S1",
                        "clearing_running_quantity": "1.0000",
                        "clearing_cost_basis": "29.0000",
                        "clearing_intraday_running_quantity": "1",
                        "clearing_intraday_cost_basis": "29.0000",
                        "clearing_direction": "credit",
                        "clearing_intraday_direction": "credit",
                        "underlying_type": "equity"
                    },
                    ...
                ],
                "total_positions": 15,
                "status": "success"
            }
        }
    """
    logger.info("Getting aggregated option positions")

    # Get aggregated positions
    positions_data = await execute_with_retry(
        rh.options.get_aggregate_positions,
    )

    if not positions_data:
        logger.warning("No aggregated option positions found")
        return {
            "result": {
                "positions": {},
                "total_symbols": 0,
                "total_contracts": 0,
                "message": "No option positions found",
                "status": "no_data",
            }
        }

    # Calculate totals
    total_symbols = len(positions_data) if isinstance(positions_data, dict) else 0
    total_contracts = 0

    if isinstance(positions_data, dict):
        for symbol_data in positions_data.values():
            if isinstance(symbol_data, dict) and "positions" in symbol_data:
                total_contracts += len(symbol_data["positions"])

    logger.info(
        f"Found aggregated positions for {total_symbols} symbols with {total_contracts} contracts"
    )

    return {
        "result": {
            "positions": positions_data,
            "total_symbols": total_symbols,
            "total_contracts": total_contracts,
            "status": "success",
        }
    }


@handle_robin_stocks_errors
async def get_all_option_positions() -> dict[str, Any]:
    """
    Get all individual option positions ever held.

    This function retrieves all option position records from Robin Stocks,
    including both long and short sides of each contract, both open and closed positions.
    Each position represents one side of an option contract.

    Returns:
        Dict containing array of individual option position records:
        {
            "result": {
                "positions": [
                    {
                        "account": "https://api.robinhood.com/accounts/894785138/",
                        "account_number": "894785138",
                        "average_price": "-29.0000",
                        "chain_id": "b905e24f-f046-458c-af25-244dbe46616c",
                        "chain_symbol": "F",
                        "id": "7dd81e42-0d94-4630-a668-873c38164a1b",
                        "option": "https://api.robinhood.com/options/instruments/845df489-f082-4141-9e39-e6b7654f5f75/",
                        "type": "short",
                        "pending_buy_quantity": "0.0000",
                        "pending_expired_quantity": "0.0000",
                        "pending_expiration_quantity": "0.0000",
                        "pending_exercise_quantity": "0.0000",
                        "pending_assignment_quantity": "0.0000",
                        "pending_sell_quantity": "0.0000",
                        "quantity": "1.0000",
                        "intraday_quantity": "1.0000",
                        "intraday_average_open_price": "-29.0000",
                        "created_at": "2025-08-09T21:06:05.831182Z",
                        "expiration_date": "2025-09-12",
                        "trade_value_multiplier": "100.0000",
                        "updated_at": "2025-08-11T13:42:16.580899Z",
                        "url": "https://api.robinhood.com/options/positions/7dd81e42-0d94-4630-a668-873c38164a1b/",
                        "option_id": "845df489-f082-4141-9e39-e6b7654f5f75",
                        "clearing_running_quantity": "1.0000",
                        "clearing_cost_basis": "29.0000",
                        "clearing_direction": "credit",
                        "clearing_intraday_running_quantity": "1.0000",
                        "clearing_intraday_cost_basis": "29.0000",
                        "clearing_intraday_direction": "credit",
                        "opened_at": "2025-08-09T21:06:05.835367Z"
                    },
                    ...
                ],
                "total_positions": 25,
                "status": "success"
            }
        }
    """
    logger.info("Getting all option positions")

    # Get all option positions
    positions_data = await execute_with_retry(
        rh.options.get_all_option_positions,
    )

    if not positions_data:
        logger.warning("No option positions found")
        return {
            "result": {
                "positions": [],
                "total_positions": 0,
                "open_positions": 0,
                "closed_positions": 0,
                "message": "No option positions found",
                "status": "no_data",
            }
        }

    # Calculate position counts
    total_positions = len(positions_data) if isinstance(positions_data, list) else 0
    open_positions = 0
    closed_positions = 0

    if isinstance(positions_data, list):
        for position in positions_data:
            if isinstance(position, dict):
                # Check if position is open based on quantity
                quantity = position.get("quantity", "0")
                if quantity and float(quantity) > 0:
                    open_positions += 1
                else:
                    closed_positions += 1

    logger.info(
        f"Found {total_positions} total positions ({open_positions} open, {closed_positions} closed)"
    )

    return {
        "result": {
            "positions": positions_data,
            "total_positions": total_positions,
            "open_positions": open_positions,
            "closed_positions": closed_positions,
            "status": "success",
        }
    }


@handle_robin_stocks_errors
async def get_open_option_positions() -> dict[str, Any]:
    """
    Get currently open option positions with summary totals.

    This function retrieves only the option positions that are currently
    open and active, along with portfolio summary information.

    Returns:
        Dict containing open option positions:
        {
            "result": {
                "positions": [
                    {
                        "account": "https://api.robinhood.com/accounts/894785138/",
                        "account_number": "894785138",
                        "average_price": "-29.0000",
                        "chain_id": "b905e24f-f046-458c-af25-244dbe46616c",
                        "chain_symbol": "F",
                        "id": "7dd81e42-0d94-4630-a668-873c38164a1b",
                        "option": "https://api.robinhood.com/options/instruments/845df489-f082-4141-9e39-e6b7654f5f75/",
                        "type": "short",
                        "pending_buy_quantity": "0.0000",
                        "pending_expired_quantity": "0.0000",
                        "pending_expiration_quantity": "0.0000",
                        "pending_exercise_quantity": "0.0000",
                        "pending_assignment_quantity": "0.0000",
                        "pending_sell_quantity": "0.0000",
                        "quantity": "1.0000",
                        "intraday_quantity": "1.0000",
                        "intraday_average_open_price": "-29.0000",
                        "created_at": "2025-08-09T21:06:05.831182Z",
                        "expiration_date": "2025-09-12",
                        "trade_value_multiplier": "100.0000",
                        "updated_at": "2025-08-11T13:42:16.580899Z",
                        "url": "https://api.robinhood.com/options/positions/7dd81e42-0d94-4630-a668-873c38164a1b/",
                        "option_id": "845df489-f082-4141-9e39-e6b7654f5f75",
                        "clearing_running_quantity": "1.0000",
                        "clearing_cost_basis": "29.0000",
                        "clearing_direction": "credit",
                        "clearing_intraday_running_quantity": "1.0000",
                        "clearing_intraday_cost_basis": "29.0000",
                        "clearing_intraday_direction": "credit",
                        "opened_at": "2025-08-09T21:06:05.835367Z"
                    },
                    ...
                ],
                "total_open_positions": 6,
                "total_equity": "0.00",
                "total_unrealized_pnl": "0.00",
                "status": "success"
            }
        }
    """
    logger.info("Getting open option positions")

    # Get open option positions
    positions_data = await execute_with_retry(
        rh.options.get_open_option_positions,
    )

    if not positions_data:
        logger.warning("No open option positions found")
        return {
            "result": {
                "positions": [],
                "total_open_positions": 0,
                "total_equity": "0.00",
                "total_unrealized_pnl": "0.00",
                "message": "No open option positions found",
                "status": "no_data",
            }
        }

    # Calculate totals
    total_open_positions = (
        len(positions_data) if isinstance(positions_data, list) else 0
    )
    total_equity = 0.0
    total_unrealized_pnl = 0.0

    if isinstance(positions_data, list):
        for position in positions_data:
            if isinstance(position, dict):
                equity = position.get("total_equity", "0")
                if equity:
                    total_equity += float(equity)

                pnl = position.get("unrealized_pnl", "0")
                if pnl:
                    total_unrealized_pnl += float(pnl)

    logger.info(
        f"Found {total_open_positions} open positions with total equity: ${total_equity:.2f}"
    )

    return {
        "result": {
            "positions": positions_data,
            "total_open_positions": total_open_positions,
            "total_equity": f"{total_equity:.2f}",
            "total_unrealized_pnl": f"{total_unrealized_pnl:.2f}",
            "status": "success",
        }
    }


@handle_robin_stocks_errors
async def get_open_option_positions_with_details() -> dict[str, Any]:
    """
    Get currently open option positions with complete option details including call/put type.

    This enhanced function retrieves open option positions and enriches each position
    with detailed option instrument data including strike price, expiration date,
    and most importantly the option type (call or put).

    Returns:
        Dict containing open option positions with enriched details:
        {
            "result": {
                "positions": [
                    {
                        "account": "https://api.robinhood.com/accounts/894785138/",
                        "account_number": "894785138",
                        "average_price": "-29.0000",
                        "chain_id": "b905e24f-f046-458c-af25-244dbe46616c",
                        "chain_symbol": "F",
                        "id": "7dd81e42-0d94-4630-a668-873c38164a1b",
                        "option": "https://api.robinhood.com/options/instruments/845df489-f082-4141-9e39-e6b7654f5f75/",
                        "type": "short",
                        "quantity": "1.0000",
                        "expiration_date": "2025-09-12",
                        "option_id": "845df489-f082-4141-9e39-e6b7654f5f75",

                        // Enhanced fields from option instrument data:
                        "option_type": "call",           // ← "call" or "put"
                        "strike_price": "11.5000",       // ← Strike price
                        "option_symbol": "F250912C00011500",  // ← OCC symbol
                        "tradability": "tradable",       // ← Trading status
                        "state": "active",               // ← Option state
                        "underlying_symbol": "F",        // ← Underlying stock

                        // ... other existing position fields
                    },
                    ...
                ],
                "total_open_positions": 6,
                "total_equity": "0.00",
                "total_unrealized_pnl": "0.00",
                "enrichment_success_rate": "100%",
                "status": "success"
            }
        }
    """
    logger.info("Getting open option positions with detailed option information")

    # Step 1: Get base open option positions
    positions_data = await execute_with_retry(
        rh.options.get_open_option_positions,
    )

    if not positions_data:
        logger.warning("No open option positions found")
        return {
            "result": {
                "positions": [],
                "total_open_positions": 0,
                "total_equity": "0.00",
                "total_unrealized_pnl": "0.00",
                "enrichment_success_rate": "0%",
                "message": "No open option positions found",
                "status": "no_data",
            }
        }

    # Step 2: Enrich each position with option instrument details
    enriched_positions = []
    enrichment_successes = 0
    total_positions = len(positions_data) if isinstance(positions_data, list) else 0

    if isinstance(positions_data, list):
        # Pre-resolve every distinct option_id concurrently so large option
        # books don't fan out into N+1 serial broker calls.
        option_id_for_position = [
            _extract_option_id(position) for position in positions_data
        ]
        unique_option_ids = dedupe_preserving_order(option_id_for_position)
        option_details_by_id = await _resolve_option_instruments(unique_option_ids)

        for position, option_id in zip(
            positions_data, option_id_for_position, strict=True
        ):
            if not isinstance(position, dict):
                enriched_positions.append(position)
                continue

            # Create enriched position starting with original data
            enriched_position = position.copy()

            if option_id:
                option_details = option_details_by_id.get(option_id)
                if option_details:
                    # Step 4: Add enriched fields to position
                    enriched_position.update(
                        {
                            "option_type": option_details.get("type", "unknown"),
                            "strike_price": option_details.get(
                                "strike_price", "0.0000"
                            ),
                            "option_symbol": option_details.get("occ_symbol", ""),
                            "tradability": option_details.get("tradability", "unknown"),
                            "state": option_details.get("state", "unknown"),
                            "underlying_symbol": option_details.get("chain_symbol", ""),
                            "expiration_date": option_details.get(
                                "expiration_date", ""
                            ),
                            "rhs_tradability": option_details.get(
                                "rhs_tradability", "unknown"
                            ),
                        }
                    )
                    enrichment_successes += 1
                    logger.debug(f"Successfully enriched position for {option_id}")
                else:
                    logger.warning(
                        f"No option details found for option_id: {option_id}"
                    )
                    enriched_position["option_type"] = "unknown"
            else:
                logger.warning("No option_id found in position data")
                enriched_position["option_type"] = "unknown"

            enriched_positions.append(enriched_position)

    # Calculate totals (same as original function)
    total_equity = 0.0
    total_unrealized_pnl = 0.0

    for position in enriched_positions:
        if isinstance(position, dict):
            equity = position.get("total_equity", "0")
            if equity:
                with contextlib.suppress(ValueError, TypeError):
                    total_equity += float(equity)

            pnl = position.get("unrealized_pnl", "0")
            if pnl:
                with contextlib.suppress(ValueError, TypeError):
                    total_unrealized_pnl += float(pnl)

    # Calculate enrichment success rate
    enrichment_rate = (
        f"{(enrichment_successes / total_positions * 100):.0f}%"
        if total_positions > 0
        else "0%"
    )

    logger.info(
        f"Found {total_positions} open positions with total equity: ${total_equity:.2f} "
        f"(enrichment success: {enrichment_rate})"
    )

    return {
        "result": {
            "positions": enriched_positions,
            "total_open_positions": total_positions,
            "total_equity": f"{total_equity:.2f}",
            "total_unrealized_pnl": f"{total_unrealized_pnl:.2f}",
            "enrichment_success_rate": enrichment_rate,
            "status": "success",
        }
    }
