"""Broker abstraction layer for multi-broker MCP support."""

from open_stocks_mcp.brokers.base import BaseBroker, BrokerAuthStatus
from open_stocks_mcp.brokers.registry import BrokerRegistry, get_broker_registry
from open_stocks_mcp.brokers.robinhood import RobinhoodBroker
from open_stocks_mcp.brokers.schwab import SchwabBroker
from open_stocks_mcp.brokers.session_state import SessionManager, get_session_manager

__all__ = [
    "BaseBroker",
    "BrokerAuthStatus",
    "BrokerRegistry",
    "RobinhoodBroker",
    "SchwabBroker",
    "SessionManager",
    "get_broker_registry",
    "get_session_manager",
]
