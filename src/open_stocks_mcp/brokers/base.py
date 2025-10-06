"""Base broker interface for multi-broker support."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class BrokerAuthStatus(Enum):
    """Authentication status for a broker."""

    NOT_CONFIGURED = "not_configured"  # No credentials provided
    NOT_AUTHENTICATED = "not_authenticated"  # Has creds, not logged in
    AUTHENTICATING = "authenticating"  # Login in progress
    AUTHENTICATED = "authenticated"  # Successfully logged in
    AUTH_FAILED = "auth_failed"  # Login failed
    TOKEN_EXPIRED = "token_expired"  # Session/token expired
    MFA_REQUIRED = "mfa_required"  # Waiting for MFA input


@dataclass
class BrokerAuthInfo:
    """Authentication information for a broker."""

    status: BrokerAuthStatus
    broker_name: str
    last_auth_attempt: datetime | None = None
    last_successful_auth: datetime | None = None
    error_message: str | None = None
    requires_setup: bool = False  # True if needs OAuth setup, API keys, etc.
    setup_instructions: str | None = None


class BaseBroker(ABC):
    """Abstract base class for broker integrations.

    All broker implementations must inherit from this class and implement
    the required methods. The broker abstraction allows the MCP server to
    work with multiple brokers (Robinhood, Schwab, etc.) transparently.

    Design Principles:
    - Server starts even if authentication fails
    - Tools check auth status before executing
    - Clear error messages when broker unavailable
    - Support for async and sync broker APIs
    """

    def __init__(self, name: str):
        """Initialize broker.

        Args:
            name: Broker identifier (e.g., "robinhood", "schwab")
        """
        self._name = name
        self._auth_info = BrokerAuthInfo(
            status=BrokerAuthStatus.NOT_CONFIGURED,
            broker_name=name,
        )

    @property
    def name(self) -> str:
        """Broker name (e.g., 'robinhood', 'schwab')"""
        return self._name

    @property
    def auth_info(self) -> BrokerAuthInfo:
        """Get current authentication information."""
        return self._auth_info

    def is_available(self) -> bool:
        """Check if broker is available for trading.

        Returns:
            True if authenticated and ready, False otherwise
        """
        return self._auth_info.status == BrokerAuthStatus.AUTHENTICATED

    def is_configured(self) -> bool:
        """Check if broker has credentials configured.

        Returns:
            True if credentials provided, False otherwise
        """
        return self._auth_info.status != BrokerAuthStatus.NOT_CONFIGURED

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with broker API.

        This method should handle the full authentication flow including:
        - Checking for existing sessions/tokens
        - Performing login if needed
        - Handling OAuth flows
        - Managing MFA if required

        Returns:
            True if authentication successful, False otherwise

        Note:
            This method should NOT raise exceptions. Instead, update
            self._auth_info with error details and return False.
        """
        pass

    @abstractmethod
    async def is_authenticated(self) -> bool:
        """Check if currently authenticated with broker.

        Returns:
            True if authenticated and session valid, False otherwise
        """
        pass

    @abstractmethod
    async def logout(self) -> None:
        """Logout and clear session/tokens.

        Should clean up any persistent session data (tokens, cookies, etc.)
        """
        pass

    def create_unavailable_response(
        self, operation: str = "operation"
    ) -> dict[str, Any]:
        """Create standardized error response for unavailable broker.

        Args:
            operation: Description of the operation being attempted

        Returns:
            Error response dict in MCP format
        """
        status = self._auth_info.status
        broker = self.name

        # Build appropriate error message
        if status == BrokerAuthStatus.NOT_CONFIGURED:
            message = (
                f"{broker.title()} is not configured. "
                f"Please set {broker.upper()}_USERNAME and {broker.upper()}_PASSWORD "
                f"environment variables."
            )
            if self._auth_info.setup_instructions:
                message += f"\n\nSetup: {self._auth_info.setup_instructions}"

        elif status == BrokerAuthStatus.AUTH_FAILED:
            message = f"{broker.title()} authentication failed: {self._auth_info.error_message}"

        elif status == BrokerAuthStatus.TOKEN_EXPIRED:
            message = (
                f"{broker.title()} session expired. "
                f"Please restart the server to re-authenticate."
            )

        elif status == BrokerAuthStatus.MFA_REQUIRED:
            message = (
                f"{broker.title()} requires MFA verification. "
                f"Please complete authentication and restart server."
            )

        elif status == BrokerAuthStatus.AUTHENTICATING:
            message = f"{broker.title()} authentication in progress. Please try again."

        else:
            message = f"{broker.title()} is not available for {operation}."

        return {
            "result": {
                "error": message,
                "status": "broker_unavailable",
                "broker": broker,
                "auth_status": status.value,
                "requires_setup": self._auth_info.requires_setup,
            }
        }

    # Abstract methods for common operations
    # Subclasses implement these using their specific broker APIs

    @abstractmethod
    async def get_account_info(self) -> dict[str, Any]:
        """Get account information.

        Returns:
            Account data in standardized format
        """
        pass

    @abstractmethod
    async def get_portfolio(self) -> dict[str, Any]:
        """Get portfolio holdings.

        Returns:
            Portfolio data in standardized format
        """
        pass

    @abstractmethod
    async def get_positions(self) -> dict[str, Any]:
        """Get current positions.

        Returns:
            Positions data in standardized format
        """
        pass

    @abstractmethod
    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Get stock quote by symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Quote data in standardized format
        """
        pass

    @abstractmethod
    async def get_stock_price(self, symbol: str) -> dict[str, Any]:
        """Get current stock price.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Price data in standardized format
        """
        pass

    @abstractmethod
    async def order_buy_market(
        self, symbol: str, quantity: float
    ) -> dict[str, Any]:
        """Place market buy order.

        Args:
            symbol: Stock ticker symbol
            quantity: Number of shares

        Returns:
            Order result in standardized format
        """
        pass

    @abstractmethod
    async def order_sell_market(
        self, symbol: str, quantity: float
    ) -> dict[str, Any]:
        """Place market sell order.

        Args:
            symbol: Stock ticker symbol
            quantity: Number of shares

        Returns:
            Order result in standardized format
        """
        pass

    # Add more abstract methods as needed for common operations
    # Each broker implements these according to their API
