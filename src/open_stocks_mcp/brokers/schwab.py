"""Schwab broker implementation using schwab-py library."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from open_stocks_mcp.brokers.base import BaseBroker, BrokerAuthStatus
from open_stocks_mcp.logging_config import logger


class SchwabBroker(BaseBroker):
    """Schwab broker adapter using schwab-py library.

    This adapter uses the schwab-py library to interact with the Charles Schwab
    API via OAuth 2.0 authentication. Unlike Robinhood, Schwab requires API
    approval from their developer portal before use.

    Authentication Flow:
    1. User registers app at developer.schwab.com
    2. Receives API key and app secret
    3. First authentication opens browser for OAuth login
    4. Token stored and automatically refreshed for ~7 days
    """

    def __init__(
        self,
        api_key: str | None = None,
        app_secret: str | None = None,
        callback_url: str = "https://127.0.0.1:8182/",
        token_path: str | None = None,
    ):
        """Initialize Schwab broker.

        Args:
            api_key: Schwab API key from developer portal
            app_secret: Schwab app secret from developer portal
            callback_url: OAuth callback URL (must match app registration)
            token_path: Path to store OAuth token (default: ~/.tokens/schwab_token.json)
        """
        super().__init__("schwab")

        self.api_key = api_key
        self.app_secret = app_secret
        self.callback_url = callback_url

        # Default token path
        if token_path is None:
            token_dir = Path.home() / ".tokens"
            token_dir.mkdir(exist_ok=True)
            self.token_path = str(token_dir / "schwab_token.json")
        else:
            self.token_path = token_path
            # Ensure token directory exists
            Path(token_path).parent.mkdir(parents=True, exist_ok=True)

        self.client = None

        # Configure auth status based on credentials
        if not api_key or not app_secret:
            self._auth_info.status = BrokerAuthStatus.NOT_CONFIGURED
            self._auth_info.setup_instructions = (
                "Set SCHWAB_API_KEY and SCHWAB_APP_SECRET environment variables. "
                "Register your app at https://developer.schwab.com/ to obtain credentials."
            )
            self._auth_info.requires_setup = True
        else:
            self._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED

    async def authenticate(self) -> bool:
        """Authenticate with Schwab using OAuth 2.0.

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Import here to avoid dependency issues if schwab-py not installed
            from schwab import auth

            self._auth_info.last_auth_attempt = datetime.now()
            self._auth_info.status = BrokerAuthStatus.AUTHENTICATING

            logger.info("Authenticating with Schwab (OAuth 2.0)...")

            # Check if token file exists
            token_exists = Path(self.token_path).exists()

            if token_exists:
                logger.info(f"Found existing token at {self.token_path}")
                try:
                    # Try to load existing token
                    self.client = auth.client_from_token_file(
                        self.token_path, self.api_key, self.app_secret
                    )
                    logger.info("✓ Schwab authentication successful (existing token)")
                    self._auth_info.status = BrokerAuthStatus.AUTHENTICATED
                    self._auth_info.last_successful_auth = datetime.now()
                    self._auth_info.error_message = None
                    return True
                except Exception as e:
                    logger.warning(f"Existing token invalid, creating new: {e}")
                    # Fall through to create new token

            # Need interactive authentication
            logger.info("No valid token found - interactive authentication required")
            logger.info("This will open a browser window for Schwab OAuth login")

            # Check if we're in a non-interactive environment
            if not os.isatty(0):  # stdin is not a terminal
                self._auth_info.status = BrokerAuthStatus.AUTH_FAILED
                self._auth_info.error_message = (
                    "Interactive authentication required but not available. "
                    "Please run authentication in an interactive terminal first."
                )
                logger.error(
                    "✗ Schwab authentication failed: non-interactive environment"
                )
                return False

            # Use easy_client for interactive authentication
            self.client = auth.easy_client(
                api_key=self.api_key,
                app_secret=self.app_secret,
                callback_url=self.callback_url,
                token_path=self.token_path,
            )

            self._auth_info.status = BrokerAuthStatus.AUTHENTICATED
            self._auth_info.last_successful_auth = datetime.now()
            self._auth_info.error_message = None
            logger.info("✓ Schwab authentication successful (new token)")
            return True

        except ImportError:
            self._auth_info.status = BrokerAuthStatus.AUTH_FAILED
            self._auth_info.error_message = (
                "schwab-py library not installed. Install with: pip install schwab-py"
            )
            logger.error("✗ Schwab authentication failed: schwab-py not installed")
            return False

        except Exception as e:
            self._auth_info.status = BrokerAuthStatus.AUTH_FAILED
            self._auth_info.error_message = str(e)
            logger.error(f"✗ Schwab authentication error: {e}")
            return False

    async def is_authenticated(self) -> bool:
        """Check if authenticated with Schwab.

        Returns:
            True if client valid, False otherwise
        """
        if self.client is None:
            return False

        # Check if token still valid
        # schwab-py automatically handles token refresh
        return self._auth_info.status == BrokerAuthStatus.AUTHENTICATED

    async def logout(self) -> None:
        """Logout from Schwab and clear session."""
        try:
            self.client = None
            self._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED
            self._auth_info.error_message = None

            # Optionally remove token file
            if Path(self.token_path).exists():
                logger.info(f"Token file still exists at {self.token_path}")
                logger.info("Delete manually if you want to fully logout")

            logger.info("Logged out from Schwab")
        except Exception as e:
            logger.error(f"Error during Schwab logout: {e}")

    # Placeholder implementations for required abstract methods
    # These will be implemented by delegating to Schwab tools

    async def get_account_info(self) -> dict[str, Any]:
        """Get account information.

        Note: Implementation delegates to Schwab account tools.
        """
        if not self.is_available():
            return self.create_unavailable_response("get_account_info")

        # TODO: Implement via schwab_account_tools
        return {
            "result": {
                "error": "Not yet implemented in Schwab broker adapter",
                "status": "not_implemented",
            }
        }

    async def get_portfolio(self) -> dict[str, Any]:
        """Get portfolio holdings."""
        if not self.is_available():
            return self.create_unavailable_response("get_portfolio")

        # TODO: Implement via schwab_account_tools
        return {
            "result": {
                "error": "Not yet implemented in Schwab broker adapter",
                "status": "not_implemented",
            }
        }

    async def get_positions(self) -> dict[str, Any]:
        """Get current positions."""
        if not self.is_available():
            return self.create_unavailable_response("get_positions")

        # TODO: Implement via schwab_account_tools
        return {
            "result": {
                "error": "Not yet implemented in Schwab broker adapter",
                "status": "not_implemented",
            }
        }

    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Get stock quote by symbol."""
        if not self.is_available():
            return self.create_unavailable_response(f"get stock quote for {symbol}")

        # TODO: Implement via schwab_market_tools
        return {
            "result": {
                "error": "Not yet implemented in Schwab broker adapter",
                "status": "not_implemented",
            }
        }

    async def get_stock_price(self, symbol: str) -> dict[str, Any]:
        """Get current stock price."""
        if not self.is_available():
            return self.create_unavailable_response(f"get stock price for {symbol}")

        # TODO: Implement via schwab_market_tools
        return {
            "result": {
                "error": "Not yet implemented in Schwab broker adapter",
                "status": "not_implemented",
            }
        }

    async def order_buy_market(self, symbol: str, quantity: float) -> dict[str, Any]:
        """Place market buy order."""
        if not self.is_available():
            return self.create_unavailable_response(f"place buy order for {symbol}")

        # TODO: Implement via schwab_trading_tools
        return {
            "result": {
                "error": "Not yet implemented in Schwab broker adapter",
                "status": "not_implemented",
            }
        }

    async def order_sell_market(self, symbol: str, quantity: float) -> dict[str, Any]:
        """Place market sell order."""
        if not self.is_available():
            return self.create_unavailable_response(f"place sell order for {symbol}")

        # TODO: Implement via schwab_trading_tools
        return {
            "result": {
                "error": "Not yet implemented in Schwab broker adapter",
                "status": "not_implemented",
            }
        }
