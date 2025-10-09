"""Robinhood broker implementation using existing robin-stocks integration."""

from datetime import datetime
from typing import Any, cast

from open_stocks_mcp.brokers.base import BaseBroker, BrokerAuthStatus
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.session_manager import SessionManager


class RobinhoodBroker(BaseBroker):
    """Robinhood broker adapter using existing SessionManager.

    This adapter wraps the existing SessionManager to conform to the
    BaseBroker interface, enabling multi-broker support without
    breaking existing functionality.
    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        session_manager: SessionManager | None = None,
    ):
        """Initialize Robinhood broker.

        Args:
            username: Robinhood username (optional if using existing session_manager)
            password: Robinhood password (optional if using existing session_manager)
            session_manager: Existing SessionManager instance (optional)
        """
        super().__init__("robinhood")

        # Use provided session manager or create new one
        self.session_manager = session_manager or SessionManager()

        # Configure credentials if provided
        if username and password:
            self.session_manager.set_credentials(username, password)
            self._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED
        elif username or password:
            # Only one credential provided - error
            self._auth_info.status = BrokerAuthStatus.NOT_CONFIGURED
            self._auth_info.error_message = (
                "Both username and password required for Robinhood"
            )
        else:
            # No credentials provided
            self._auth_info.status = BrokerAuthStatus.NOT_CONFIGURED
            self._auth_info.setup_instructions = (
                "Set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD environment variables"
            )

    async def authenticate(self) -> bool:
        """Authenticate with Robinhood using SessionManager.

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            self._auth_info.last_auth_attempt = datetime.now()
            self._auth_info.status = BrokerAuthStatus.AUTHENTICATING

            logger.info("Authenticating with Robinhood...")

            # Use existing SessionManager logic
            success = await self.session_manager.ensure_authenticated()

            if success:
                self._auth_info.status = BrokerAuthStatus.AUTHENTICATED
                self._auth_info.last_successful_auth = datetime.now()
                self._auth_info.error_message = None
                logger.info("✓ Robinhood authentication successful")
                return True
            else:
                self._auth_info.status = BrokerAuthStatus.AUTH_FAILED
                self._auth_info.error_message = (
                    "Authentication failed - check username/password"
                )
                logger.error("✗ Robinhood authentication failed")
                return False

        except Exception as e:
            self._auth_info.status = BrokerAuthStatus.AUTH_FAILED
            self._auth_info.error_message = str(e)
            logger.error(f"✗ Robinhood authentication error: {e}")
            return False

    async def is_authenticated(self) -> bool:
        """Check if authenticated with Robinhood.

        Returns:
            True if session valid, False otherwise
        """
        is_valid = self.session_manager.is_session_valid()

        # Update status if session expired
        if not is_valid and self._auth_info.status == BrokerAuthStatus.AUTHENTICATED:
            self._auth_info.status = BrokerAuthStatus.TOKEN_EXPIRED
            self._auth_info.error_message = "Session expired"

        return is_valid

    async def logout(self) -> None:
        """Logout from Robinhood and clear session."""
        try:
            await self.session_manager.logout()
            self._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED
            self._auth_info.error_message = None
            logger.info("Logged out from Robinhood")
        except Exception as e:
            logger.error(f"Error during Robinhood logout: {e}")

    # Placeholder implementations for required abstract methods
    # These will be implemented by delegating to existing tool functions

    async def get_account_info(self) -> dict[str, Any]:
        """Get account information.

        Note: Implementation delegates to existing tool functions.
        This will be connected in Phase 2 of the migration.
        """
        if not self.is_available():
            return self.create_unavailable_response("get_account_info")

        # TODO: Phase 2 - delegate to existing get_account_info() function
        from open_stocks_mcp.tools.robinhood_account_tools import get_account_info

        return cast(dict[str, Any], await get_account_info())

    async def get_portfolio(self) -> dict[str, Any]:
        """Get portfolio holdings."""
        if not self.is_available():
            return self.create_unavailable_response("get_portfolio")

        # TODO: Phase 2 - delegate to existing get_portfolio() function
        from open_stocks_mcp.tools.robinhood_account_tools import get_portfolio

        return cast(dict[str, Any], await get_portfolio())

    async def get_positions(self) -> dict[str, Any]:
        """Get current positions."""
        if not self.is_available():
            return self.create_unavailable_response("get_positions")

        # TODO: Phase 2 - delegate to existing get_positions() function
        from open_stocks_mcp.tools.robinhood_account_tools import get_positions

        return cast(dict[str, Any], await get_positions())

    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Get stock quote by symbol."""
        if not self.is_available():
            return self.create_unavailable_response(f"get stock quote for {symbol}")

        # TODO: Phase 2 - delegate to existing get_stock_quote_by_id() function
        # For now, return placeholder
        return {
            "result": {
                "error": "Not yet implemented in broker adapter",
                "status": "not_implemented",
            }
        }

    async def get_stock_price(self, symbol: str) -> dict[str, Any]:
        """Get current stock price."""
        if not self.is_available():
            return self.create_unavailable_response(f"get stock price for {symbol}")

        # TODO: Phase 2 - delegate to existing get_stock_price() function
        from open_stocks_mcp.tools.robinhood_stock_tools import get_stock_price

        return cast(dict[str, Any], await get_stock_price(symbol))

    async def order_buy_market(
        self, symbol: str, quantity: float
    ) -> dict[str, Any]:
        """Place market buy order."""
        if not self.is_available():
            return self.create_unavailable_response(
                f"place buy order for {symbol}"
            )

        # TODO: Phase 2 - delegate to existing order_buy_market() function
        from open_stocks_mcp.tools.robinhood_trading_tools import order_buy_market

        return cast(dict[str, Any], await order_buy_market(symbol, int(quantity)))

    async def order_sell_market(
        self, symbol: str, quantity: float
    ) -> dict[str, Any]:
        """Place market sell order."""
        if not self.is_available():
            return self.create_unavailable_response(
                f"place sell order for {symbol}"
            )

        # TODO: Phase 2 - delegate to existing order_sell_market() function
        from open_stocks_mcp.tools.robinhood_trading_tools import order_sell_market

        return cast(dict[str, Any], await order_sell_market(symbol, int(quantity)))
