"""Robinhood broker implementation using existing robin-stocks integration."""

from datetime import datetime
from typing import Any

from open_stocks_mcp.brokers.base import BaseBroker, BrokerAuthStatus
from open_stocks_mcp.brokers.request_policy import install_robinhood_request_timeout
from open_stocks_mcp.brokers.session_state import SessionManager
from open_stocks_mcp.config import get_config
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.robinhood_account_tools import (
    get_account_info,
    get_portfolio,
    get_positions,
)
from open_stocks_mcp.tools.stocks.quote import get_stock_price
from open_stocks_mcp.tools.trading.orders_stock import (
    order_buy_market,
    order_sell_market,
)


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

        # Install request timeout policy
        config = get_config()
        install_robinhood_request_timeout(
            config.broker_requests.robinhood_timeout_seconds
        )

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

    async def get_account_info(self) -> dict[str, Any]:
        """Get account information."""
        if not self.is_available():
            return self.create_unavailable_response("get_account_info")

        return await get_account_info()

    async def get_portfolio(self) -> dict[str, Any]:
        """Get portfolio holdings."""
        if not self.is_available():
            return self.create_unavailable_response("get_portfolio")

        return await get_portfolio()

    async def get_positions(self) -> dict[str, Any]:
        """Get current positions."""
        if not self.is_available():
            return self.create_unavailable_response("get_positions")

        return await get_positions()

    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Get stock quote by symbol."""
        if not self.is_available():
            return self.create_unavailable_response(f"get stock quote for {symbol}")

        return await get_stock_price(symbol)

    async def get_stock_price(self, symbol: str) -> dict[str, Any]:
        """Get current stock price."""
        if not self.is_available():
            return self.create_unavailable_response(f"get stock price for {symbol}")

        return await get_stock_price(symbol)

    async def order_buy_market(self, symbol: str, quantity: float) -> dict[str, Any]:
        """Place market buy order."""
        if not self.is_available():
            return self.create_unavailable_response(f"place buy order for {symbol}")

        return await order_buy_market(symbol, int(quantity))

    async def order_sell_market(self, symbol: str, quantity: float) -> dict[str, Any]:
        """Place market sell order."""
        if not self.is_available():
            return self.create_unavailable_response(f"place sell order for {symbol}")

        return await order_sell_market(symbol, int(quantity))
