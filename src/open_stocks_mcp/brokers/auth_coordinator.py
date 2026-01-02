"""Authentication coordinator for managing multi-broker login flows."""

from datetime import datetime
from typing import Any

from open_stocks_mcp.brokers.base import BrokerAuthStatus
from open_stocks_mcp.brokers.registry import get_broker_registry
from open_stocks_mcp.logging_config import logger


async def attempt_broker_logins(
    require_at_least_one: bool = False,
) -> tuple[int, int, list[str]]:
    """Attempt to authenticate all configured brokers.

    This function is designed to be NON-BLOCKING. The server will start
    regardless of authentication results.

    Args:
        require_at_least_one: If True, warn if no brokers authenticate

    Returns:
        Tuple of (successful_count, total_count, failed_broker_names)
    """
    logger.info("=" * 60)
    logger.info("Starting Multi-Broker Authentication")
    logger.info("=" * 60)

    registry = await get_broker_registry()

    # Check if any brokers are registered
    brokers = registry.list_brokers()
    if not brokers:
        logger.warning(
            "⚠️  No brokers registered - server running without broker access"
        )
        return 0, 0, []

    logger.info(f"Registered brokers: {', '.join(brokers)}")

    # Attempt authentication for all brokers
    start_time = datetime.now()
    results = await registry.authenticate_all(fail_fast=False)
    elapsed = (datetime.now() - start_time).total_seconds()

    # Count results
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    failed = [name for name, success in results.items() if not success]

    # Log summary
    logger.info("=" * 60)
    logger.info(f"Authentication Summary ({elapsed:.1f}s)")
    logger.info("=" * 60)

    for broker_name, success in results.items():
        if success:
            logger.info(f"  ✓ {broker_name.upper()}: Authenticated")
        else:
            broker = registry.get_broker(broker_name)
            if broker:
                status = broker.auth_info.status
                error = broker.auth_info.error_message or "Unknown error"

                if status == BrokerAuthStatus.NOT_CONFIGURED:
                    logger.info(f"  ○ {broker_name.upper()}: Not configured (skipped)")
                elif status == BrokerAuthStatus.MFA_REQUIRED:
                    logger.warning(f"  ⚠ {broker_name.upper()}: MFA required")
                else:
                    logger.error(f"  ✗ {broker_name.upper()}: {error}")

    logger.info("=" * 60)

    # Overall status
    if successful == total and total > 0:
        logger.info(f"✅ All {total} broker(s) authenticated successfully")
    elif successful > 0:
        logger.warning(
            f"⚠️  Partial success: {successful}/{total} broker(s) authenticated"
        )
        logger.warning(f"   Unavailable: {', '.join(failed)}")
    elif total > 0:
        logger.error(f"❌ No brokers authenticated ({total} attempted)")
        logger.error(f"   Failed: {', '.join(failed)}")

        if require_at_least_one:
            logger.error(
                "   Server will start but all broker-specific tools will be unavailable"
            )
    else:
        logger.warning("⚠️  No authentication attempts made")

    logger.info("=" * 60)

    return successful, total, failed


def create_unauthenticated_tool_response(
    broker_name: str | None = None,
) -> dict[str, Any]:
    """Create error response when no broker is authenticated.

    Args:
        broker_name: Specific broker requested, or None for any

    Returns:
        Error response dict
    """
    if broker_name:
        message = (
            f"{broker_name.title()} is not available. "
            f"Please check authentication status with the 'broker_status' tool."
        )
    else:
        message = (
            "No authenticated brokers available. "
            "Please check authentication status with the 'broker_status' tool."
        )

    return {
        "result": {
            "error": message,
            "status": "no_authenticated_brokers",
            "help": "Check logs for authentication errors or run 'broker_status' tool",
        }
    }


async def get_authenticated_broker_or_error(
    broker_name: str | None = None,
    operation: str = "operation",
) -> tuple[Any, dict[str, Any] | None]:
    """Get an authenticated broker or return an error response.

    Args:
        broker_name: Specific broker name, or None for active broker
        operation: Operation being attempted (for error message)

    Returns:
        Tuple of (broker, None) if available, or (None, error_response)
    """
    registry = await get_broker_registry()
    return registry.get_broker_or_error(broker_name, operation)
