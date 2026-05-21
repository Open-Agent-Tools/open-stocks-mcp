"""Helper functions implementing the bodies of server-app system tools.

These helpers exist so `server/app.py` can stay focused on `@mcp.tool()`
registration. Each helper returns the same `{"result": {...}}` shape its
corresponding `@mcp.tool()` wrapper used to return inline.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from open_stocks_mcp.brokers.registry import get_broker_registry
from open_stocks_mcp.health import get_health_service
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.monitoring import get_metrics_collector
from open_stocks_mcp.tools.circuit_breaker import get_broker_circuit_breaker
from open_stocks_mcp.tools.rate_limiter import get_rate_limiter
from open_stocks_mcp.tools.robinhood_tools import list_available_tools
from open_stocks_mcp.tools.session_manager import get_session_manager


async def get_list_tools_data(mcp: FastMCP) -> dict[str, Any]:
    """Return the list of tools registered on the given FastMCP server."""
    return await list_available_tools(mcp)


async def get_session_status_data() -> dict[str, Any]:
    """Return current session status and authentication information."""
    session_manager = get_session_manager()
    session_info = session_manager.get_session_info()

    return {
        "result": {
            **session_info,
            "circuit_breaker": get_broker_circuit_breaker().snapshot(),
            "status": "success",
        }
    }


async def get_broker_status_data() -> dict[str, Any]:
    """Return authentication status for all configured brokers."""
    try:
        registry = await get_broker_registry()
        auth_status = registry.get_auth_status()
        available_brokers = registry.get_available_brokers()
        broker_health = {}
        account_health = {}
        get_broker_health = getattr(registry, "get_broker_health", None)
        if callable(get_broker_health):
            health_summary = get_broker_health()
            if isinstance(health_summary, dict):
                broker_health = health_summary.get("broker_health", {})
                account_health = health_summary.get("account_health", {})

        return {
            "result": {
                "brokers": auth_status,
                "available_brokers": available_brokers,
                "broker_health": {
                    name: broker.get_health_status()
                    for name in registry.list_brokers()
                    if (broker := registry.get_broker(name)) is not None
                },
                "total_configured": len(registry.list_brokers()),
                "total_authenticated": len(available_brokers),
                "broker_health": broker_health,
                "account_health": account_health,
                "status": "success",
            }
        }
    except Exception as e:
        logger.error(f"Error getting broker status: {e}")
        return {
            "result": {
                "error": str(e),
                "status": "error",
            }
        }


async def get_list_brokers_data() -> dict[str, Any]:
    """Return all registered brokers and their availability."""
    try:
        registry = await get_broker_registry()
        brokers = registry.list_brokers()
        available = registry.get_available_brokers()

        broker_info = []
        for broker_name in brokers:
            broker = registry.get_broker(broker_name)
            if broker:
                broker_info.append(
                    {
                        "name": broker_name,
                        "available": broker_name in available,
                        "status": broker.auth_info.status.value,
                        "configured": broker.is_configured(),
                    }
                )

        return {
            "result": {
                "brokers": broker_info,
                "count": len(brokers),
                "status": "success",
            }
        }
    except Exception as e:
        logger.error(f"Error listing brokers: {e}")
        return {
            "result": {
                "error": str(e),
                "status": "error",
            }
        }


async def get_rate_limit_status_data() -> dict[str, Any]:
    """Return current rate limit usage and statistics."""
    rate_limiter = get_rate_limiter()
    stats = rate_limiter.get_stats()

    return {
        "result": {
            **stats,
            "endpoint_usage": stats.get("endpoint_usage", {}),
            "circuit_breaker": get_broker_circuit_breaker().snapshot(),
            "status": "success",
        }
    }


async def get_metrics_summary_data() -> dict[str, Any]:
    """Return a comprehensive metrics summary for monitoring."""
    metrics_collector = get_metrics_collector()
    metrics = await metrics_collector.get_metrics()

    return {
        "result": {
            **metrics,
            "broker_health": metrics.get("broker_health", {}),
            "account_health": metrics.get("account_health", {}),
            "status": "success",
        }
    }


async def get_health_check_data() -> dict[str, Any]:
    """Return health status of the MCP server."""
    health_status = await get_health_service().get_status()
    metrics = await get_metrics_collector().get_metrics()
    return {
        "result": {
            **health_status,
            "broker_health": metrics.get("broker_health", {}),
            "account_health": metrics.get("account_health", {}),
            "circuit_breaker": get_broker_circuit_breaker().snapshot(),
            "broker_health": metrics.get("broker_health", {}),
            "account_health": metrics.get("account_health", {}),
            "health_status": health_status["status"],
            "status": "success",
        }
    }
