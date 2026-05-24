"""Tool-layer broker helper utilities."""

from typing import Any

from open_stocks_mcp.brokers.registry import get_broker_registry
from open_stocks_mcp.brokers.request_policy import execute_broker_request

__all__ = ["execute_broker_request", "get_authenticated_broker_or_error"]


async def get_authenticated_broker_or_error(
    broker_name: str | None = None,
    operation: str = "operation",
) -> tuple[Any, dict[str, Any] | None]:
    """Get an authenticated broker or return an error response tuple."""
    registry = await get_broker_registry()
    result: tuple[Any, dict[str, Any] | None] = registry.get_broker_or_error(
        broker_name, operation
    )
    return result
