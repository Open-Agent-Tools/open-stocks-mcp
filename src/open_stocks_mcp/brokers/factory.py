"""Pluggable broker factory registry.

New brokers can be added without modifying core server code by:
1. Subclassing BaseBroker
2. Implementing a BrokerFactory function (BrokerBuildContext -> BaseBroker | None)
3. Calling register_broker_factory("name", factory_fn) at module load time

The server's setup_brokers() iterates enabled_brokers and dispatches through
this registry, so no changes to server/app.py or config.py are required.

Example (third-party broker plugin)::

    from open_stocks_mcp.brokers.factory import register_broker_factory, BrokerBuildContext

    class AlpacaBroker(BaseBroker):
        ...

    def _build_alpaca(ctx: BrokerBuildContext) -> AlpacaBroker | None:
        api_key = ctx.cli_credentials.get("alpaca_api_key")
        if not api_key:
            return None
        return AlpacaBroker(api_key=api_key)

    register_broker_factory("alpaca", _build_alpaca)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from open_stocks_mcp.brokers.base import BaseBroker
    from open_stocks_mcp.config import ServerConfig

BrokerFactory = Callable[["BrokerBuildContext"], "BaseBroker | None"]

_BROKER_FACTORIES: dict[str, BrokerFactory] = {}


@dataclass
class BrokerBuildContext:
    """Context passed to each broker factory during server startup."""

    config: ServerConfig
    cli_credentials: dict[str, str] = field(default_factory=dict)


def register_broker_factory(name: str, factory: BrokerFactory) -> None:
    """Register a factory function for a named broker.

    The factory receives a BrokerBuildContext and returns a configured
    BaseBroker instance, or None if the broker cannot be built (e.g.
    missing credentials).

    Args:
        name: Broker identifier (e.g. "alpaca"). Must be lowercase.
        factory: Callable that builds and returns the broker.
    """
    _BROKER_FACTORIES[name.lower()] = factory


def get_registered_broker_names() -> frozenset[str]:
    """Return the set of broker names that have a registered factory."""
    return frozenset(_BROKER_FACTORIES)


def is_broker_factory_registered(name: str) -> bool:
    """Return True if a factory is registered for the given broker name."""
    return name.lower() in _BROKER_FACTORIES


def build_broker(name: str, ctx: BrokerBuildContext) -> BaseBroker | None:
    """Build a broker instance using the registered factory.

    Args:
        name: Broker name (e.g. "robinhood", "schwab").
        ctx: Build context containing server config and CLI credentials.

    Returns:
        Configured broker instance, or None if no factory is registered
        or the factory decides the broker cannot be built (missing credentials).
    """
    factory = _BROKER_FACTORIES.get(name.lower())
    if factory is None:
        return None
    return factory(ctx)


# ---------------------------------------------------------------------------
# Built-in broker factories
# These use lazy imports so that broker modules are not imported until needed,
# and so that this file can be imported without triggering the full broker
# dependency chain.
# ---------------------------------------------------------------------------


def _build_robinhood(ctx: BrokerBuildContext) -> BaseBroker | None:
    from open_stocks_mcp.logging_config import logger

    username = (
        ctx.cli_credentials.get("username") or ctx.config.brokers.robinhood.username
    )
    password = (
        ctx.cli_credentials.get("password") or ctx.config.brokers.robinhood.password
    )
    if not username or not password:
        logger.warning(
            "⚠️  Robinhood credentials not provided - skipping Robinhood integration"
        )
        logger.info(
            "   Set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD to enable Robinhood"
        )
        return None
    from open_stocks_mcp.brokers.robinhood import RobinhoodBroker
    from open_stocks_mcp.tools.session_manager import get_session_manager

    return RobinhoodBroker(
        username=username,
        password=password,
        session_manager=get_session_manager(),
    )


def _build_schwab(ctx: BrokerBuildContext) -> BaseBroker | None:
    from open_stocks_mcp.logging_config import logger

    sc = ctx.config.brokers.schwab
    if not sc.api_key or not sc.app_secret:
        logger.info(
            "Schwab enablement gate honored but Schwab credentials not configured - skipping"
        )
        return None
    from open_stocks_mcp.brokers.schwab import SchwabBroker

    return SchwabBroker(
        api_key=sc.api_key,
        app_secret=sc.app_secret,
        callback_url=sc.callback_url,
        token_path=sc.token_path,
    )


register_broker_factory("robinhood", _build_robinhood)
register_broker_factory("schwab", _build_schwab)
