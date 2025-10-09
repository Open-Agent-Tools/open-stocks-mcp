"""Broker registry for managing multiple broker instances."""

import asyncio
from typing import Any

from open_stocks_mcp.brokers.base import BaseBroker, BrokerAuthStatus
from open_stocks_mcp.logging_config import logger


class BrokerRegistry:
    """Manages multiple broker instances and their authentication status.

    The registry allows the MCP server to:
    - Register multiple brokers (Robinhood, Schwab, etc.)
    - Attempt authentication for all brokers at startup
    - Continue running even if some/all brokers fail to authenticate
    - Track authentication status per broker
    - Route tool calls to appropriate brokers
    """

    def __init__(self) -> None:
        """Initialize broker registry."""
        self._brokers: dict[str, BaseBroker] = {}
        self._active_broker: str | None = None
        self._authentication_attempts: dict[str, int] = {}

    def register(self, broker: BaseBroker) -> None:
        """Register a broker instance.

        Args:
            broker: Broker instance to register
        """
        logger.info(f"Registering broker: {broker.name}")
        self._brokers[broker.name] = broker
        self._authentication_attempts[broker.name] = 0

        # Set as active if first broker or none set
        if self._active_broker is None:
            self._active_broker = broker.name
            logger.info(f"Set active broker: {broker.name}")

    def get_broker(self, name: str | None = None) -> BaseBroker | None:
        """Get broker by name, or active broker if name is None.

        Args:
            name: Broker name, or None for active broker

        Returns:
            Broker instance, or None if not found
        """
        broker_name = name or self._active_broker
        if not broker_name:
            logger.warning("No active broker set")
            return None

        broker = self._brokers.get(broker_name)
        if not broker:
            logger.warning(f"Broker not found: {broker_name}")
            return None

        return broker

    def get_broker_or_error(
        self, name: str | None = None, operation: str = "operation"
    ) -> tuple[BaseBroker | None, dict[str, Any] | None]:
        """Get broker or return error response if unavailable.

        Args:
            name: Broker name, or None for active broker
            operation: Operation being attempted (for error message)

        Returns:
            Tuple of (broker, None) if available, or (None, error_response)
        """
        broker = self.get_broker(name)

        if not broker:
            return None, {
                "result": {
                    "error": f"Broker not found: {name or 'active'}",
                    "status": "broker_not_found",
                }
            }

        if not broker.is_available():
            return None, broker.create_unavailable_response(operation)

        return broker, None

    def set_active_broker(self, name: str) -> bool:
        """Set the active broker.

        Args:
            name: Broker name to set as active

        Returns:
            True if successful, False if broker not registered
        """
        if name not in self._brokers:
            logger.error(f"Cannot set active broker - not registered: {name}")
            return False

        self._active_broker = name
        logger.info(f"Active broker changed to: {name}")
        return True

    def list_brokers(self) -> list[str]:
        """List all registered brokers.

        Returns:
            List of broker names
        """
        return list(self._brokers.keys())

    def get_available_brokers(self) -> list[str]:
        """List brokers that are authenticated and available.

        Returns:
            List of available broker names
        """
        return [
            name
            for name, broker in self._brokers.items()
            if broker.is_available()
        ]

    def get_auth_status(self) -> dict[str, Any]:
        """Get authentication status for all brokers.

        Returns:
            Dict mapping broker names to their auth info
        """
        return {
            name: {
                "status": broker.auth_info.status.value,
                "last_auth_attempt": (
                    broker.auth_info.last_auth_attempt.isoformat()
                    if broker.auth_info.last_auth_attempt
                    else None
                ),
                "last_successful_auth": (
                    broker.auth_info.last_successful_auth.isoformat()
                    if broker.auth_info.last_successful_auth
                    else None
                ),
                "error_message": broker.auth_info.error_message,
                "is_available": broker.is_available(),
                "is_configured": broker.is_configured(),
                "requires_setup": broker.auth_info.requires_setup,
                "setup_instructions": broker.auth_info.setup_instructions,
            }
            for name, broker in self._brokers.items()
        }

    async def authenticate_all(
        self, fail_fast: bool = False
    ) -> dict[str, bool]:
        """Authenticate all registered brokers.

        This method is designed to be NON-BLOCKING - the server will start
        even if all authentications fail.

        Args:
            fail_fast: If True, stop on first failure (default: False)

        Returns:
            Dict mapping broker names to authentication success status
        """
        logger.info("Starting authentication for all registered brokers")
        results: dict[str, bool] = {}

        for name, broker in self._brokers.items():
            if not broker.is_configured():
                logger.warning(
                    f"Broker {name} not configured - skipping authentication"
                )
                results[name] = False
                continue

            logger.info(f"Authenticating broker: {name}")
            self._authentication_attempts[name] += 1

            try:
                success = await broker.authenticate()
                results[name] = success

                if success:
                    logger.info(f"✓ {name} authenticated successfully")
                else:
                    logger.warning(
                        f"✗ {name} authentication failed: {broker.auth_info.error_message}"
                    )
                    if fail_fast:
                        logger.error("Fail-fast enabled, stopping authentication")
                        break

            except Exception as e:
                # Catch any unexpected exceptions from broker.authenticate()
                logger.error(
                    f"✗ {name} authentication raised exception: {e}",
                    exc_info=True,
                )
                results[name] = False

                # Update broker status
                broker._auth_info.status = BrokerAuthStatus.AUTH_FAILED
                broker._auth_info.error_message = str(e)

                if fail_fast:
                    logger.error("Fail-fast enabled, stopping authentication")
                    break

        # Log summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        logger.info(
            f"Authentication complete: {successful}/{total} brokers authenticated"
        )

        if successful == 0 and total > 0:
            logger.warning(
                "⚠️  No brokers authenticated - server running in limited mode"
            )
        elif successful < total:
            logger.warning(
                f"⚠️  Partial authentication - {total - successful} broker(s) unavailable"
            )

        return results

    async def ensure_authenticated(self, broker_name: str) -> bool:
        """Ensure a specific broker is authenticated.

        Args:
            broker_name: Name of broker to authenticate

        Returns:
            True if authenticated, False otherwise
        """
        broker = self.get_broker(broker_name)
        if not broker:
            logger.error(f"Cannot authenticate unknown broker: {broker_name}")
            return False

        if broker.is_available():
            return True

        if not broker.is_configured():
            logger.warning(
                f"Cannot authenticate {broker_name} - not configured"
            )
            return False

        logger.info(f"Re-authenticating broker: {broker_name}")
        try:
            return await broker.authenticate()
        except Exception as e:
            logger.error(
                f"Failed to re-authenticate {broker_name}: {e}", exc_info=True
            )
            return False

    async def logout_all(self) -> None:
        """Logout all brokers and clear sessions."""
        logger.info("Logging out all brokers")

        logout_tasks = [
            broker.logout() for broker in self._brokers.values()
        ]

        results = await asyncio.gather(*logout_tasks, return_exceptions=True)

        for broker_name, result in zip(self._brokers.keys(), results, strict=False):
            if isinstance(result, Exception):
                logger.error(f"Error logging out {broker_name}: {result}")
            else:
                logger.info(f"✓ {broker_name} logged out successfully")


# Global registry instance
_registry: BrokerRegistry | None = None
_registry_lock = asyncio.Lock()


async def get_broker_registry() -> BrokerRegistry:
    """Get or create the global broker registry.

    Returns:
        Global BrokerRegistry instance
    """
    global _registry

    if _registry is None:
        async with _registry_lock:
            if _registry is None:
                _registry = BrokerRegistry()
                logger.info("Created global broker registry")

    return _registry


def get_broker_registry_sync() -> BrokerRegistry:
    """Get the global broker registry (synchronous version).

    Note: This should only be used when async is not available.
    Registry must be initialized via get_broker_registry() first.

    Returns:
        Global BrokerRegistry instance

    Raises:
        RuntimeError: If registry not initialized
    """
    if _registry is None:
        raise RuntimeError(
            "Broker registry not initialized. "
            "Call get_broker_registry() first."
        )
    return _registry
