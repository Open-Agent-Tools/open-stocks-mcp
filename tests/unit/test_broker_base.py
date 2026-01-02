"""Unit tests for broker base classes and authentication status."""

from datetime import datetime

import pytest

from open_stocks_mcp.brokers.base import BaseBroker, BrokerAuthInfo, BrokerAuthStatus


class MockBroker(BaseBroker):
    """Mock broker for testing base functionality."""

    def __init__(self, name: str = "mock"):
        super().__init__(name)
        self._should_auth_succeed = True
        self._auth_call_count = 0

    async def authenticate(self) -> bool:
        """Mock authentication."""
        self._auth_call_count += 1
        self._auth_info.last_auth_attempt = datetime.now()
        self._auth_info.status = BrokerAuthStatus.AUTHENTICATING

        if self._should_auth_succeed:
            self._auth_info.status = BrokerAuthStatus.AUTHENTICATED
            self._auth_info.last_successful_auth = datetime.now()
            self._auth_info.error_message = None
            return True
        else:
            self._auth_info.status = BrokerAuthStatus.AUTH_FAILED
            self._auth_info.error_message = "Mock authentication failed"
            return False

    async def is_authenticated(self) -> bool:
        """Check if authenticated."""
        return self._auth_info.status == BrokerAuthStatus.AUTHENTICATED

    async def logout(self) -> None:
        """Mock logout."""
        self._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED
        self._auth_info.error_message = None

    # Placeholder implementations for abstract methods
    async def get_account_info(self):
        return {"result": {"mock": "account_info"}}

    async def get_portfolio(self):
        return {"result": {"mock": "portfolio"}}

    async def get_positions(self):
        return {"result": {"mock": "positions"}}

    async def get_stock_quote(self, symbol: str):
        return {"result": {"symbol": symbol, "price": 100.0}}

    async def get_stock_price(self, symbol: str):
        return {"result": {"symbol": symbol, "price": 100.0}}

    async def order_buy_market(self, symbol: str, quantity: float):
        return {"result": {"order": "buy"}}

    async def order_sell_market(self, symbol: str, quantity: float):
        return {"result": {"order": "sell"}}


class TestBrokerAuthStatus:
    """Test BrokerAuthStatus enum."""

    def test_auth_status_values(self):
        """Test all auth status enum values."""
        assert BrokerAuthStatus.NOT_CONFIGURED.value == "not_configured"
        assert BrokerAuthStatus.NOT_AUTHENTICATED.value == "not_authenticated"
        assert BrokerAuthStatus.AUTHENTICATING.value == "authenticating"
        assert BrokerAuthStatus.AUTHENTICATED.value == "authenticated"
        assert BrokerAuthStatus.AUTH_FAILED.value == "auth_failed"
        assert BrokerAuthStatus.TOKEN_EXPIRED.value == "token_expired"
        assert BrokerAuthStatus.MFA_REQUIRED.value == "mfa_required"

    def test_auth_status_count(self):
        """Test we have all 7 expected auth statuses."""
        assert len(BrokerAuthStatus) == 7


class TestBrokerAuthInfo:
    """Test BrokerAuthInfo dataclass."""

    def test_default_initialization(self):
        """Test default auth info values."""
        info = BrokerAuthInfo(
            status=BrokerAuthStatus.NOT_CONFIGURED, broker_name="test_broker"
        )
        assert info.status == BrokerAuthStatus.NOT_CONFIGURED
        assert info.broker_name == "test_broker"
        assert info.last_auth_attempt is None
        assert info.last_successful_auth is None
        assert info.error_message is None
        assert info.setup_instructions is None
        assert info.requires_setup is False

    def test_custom_initialization(self):
        """Test custom auth info values."""
        now = datetime.now()
        info = BrokerAuthInfo(
            status=BrokerAuthStatus.AUTHENTICATED,
            broker_name="test_broker",
            last_auth_attempt=now,
            last_successful_auth=now,
            error_message="test error",
            setup_instructions="test setup",
            requires_setup=True,
        )
        assert info.status == BrokerAuthStatus.AUTHENTICATED
        assert info.broker_name == "test_broker"
        assert info.last_auth_attempt == now
        assert info.last_successful_auth == now
        assert info.error_message == "test error"
        assert info.setup_instructions == "test setup"
        assert info.requires_setup is True


class TestBaseBroker:
    """Test BaseBroker abstract class via MockBroker."""

    @pytest.mark.asyncio
    async def test_broker_initialization(self):
        """Test broker initializes with correct default state."""
        broker = MockBroker("test_broker")
        assert broker.name == "test_broker"
        assert broker.auth_info.status == BrokerAuthStatus.NOT_CONFIGURED
        assert not broker.is_available()

    @pytest.mark.asyncio
    async def test_successful_authentication(self):
        """Test successful authentication flow."""
        broker = MockBroker()
        broker._should_auth_succeed = True

        # Before authentication
        assert not broker.is_available()
        assert broker.auth_info.status == BrokerAuthStatus.NOT_CONFIGURED

        # Authenticate
        success = await broker.authenticate()
        assert success is True
        assert broker._auth_call_count == 1

        # After authentication
        assert broker.is_available()
        assert broker.auth_info.status == BrokerAuthStatus.AUTHENTICATED
        assert broker.auth_info.last_auth_attempt is not None
        assert broker.auth_info.last_successful_auth is not None
        assert broker.auth_info.error_message is None

    @pytest.mark.asyncio
    async def test_failed_authentication(self):
        """Test failed authentication flow."""
        broker = MockBroker()
        broker._should_auth_succeed = False

        # Authenticate
        success = await broker.authenticate()
        assert success is False
        assert broker._auth_call_count == 1

        # Check state
        assert not broker.is_available()
        assert broker.auth_info.status == BrokerAuthStatus.AUTH_FAILED
        assert broker.auth_info.last_auth_attempt is not None
        assert broker.auth_info.last_successful_auth is None
        assert broker.auth_info.error_message == "Mock authentication failed"

    @pytest.mark.asyncio
    async def test_logout(self):
        """Test logout clears authentication."""
        broker = MockBroker()
        broker._should_auth_succeed = True

        # Authenticate first
        await broker.authenticate()
        assert broker.is_available()

        # Logout
        await broker.logout()
        assert not broker.is_available()
        assert broker.auth_info.status == BrokerAuthStatus.NOT_AUTHENTICATED
        assert broker.auth_info.error_message is None

    @pytest.mark.asyncio
    async def test_is_available_when_authenticated(self):
        """Test is_available returns True when authenticated."""
        broker = MockBroker()
        broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        assert broker.is_available() is True

    @pytest.mark.asyncio
    async def test_is_available_when_not_authenticated(self):
        """Test is_available returns False for various non-authenticated states."""
        broker = MockBroker()

        for status in [
            BrokerAuthStatus.NOT_CONFIGURED,
            BrokerAuthStatus.NOT_AUTHENTICATED,
            BrokerAuthStatus.AUTHENTICATING,
            BrokerAuthStatus.AUTH_FAILED,
            BrokerAuthStatus.TOKEN_EXPIRED,
            BrokerAuthStatus.MFA_REQUIRED,
        ]:
            broker._auth_info.status = status
            assert broker.is_available() is False, (
                f"Should not be available when {status}"
            )

    @pytest.mark.asyncio
    async def test_is_configured_with_credentials(self):
        """Test is_configured returns True when not in NOT_CONFIGURED state."""
        broker = MockBroker()
        broker._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED
        assert broker.is_configured() is True

    @pytest.mark.asyncio
    async def test_is_configured_without_credentials(self):
        """Test is_configured returns False when in NOT_CONFIGURED state."""
        broker = MockBroker()
        broker._auth_info.status = BrokerAuthStatus.NOT_CONFIGURED
        assert broker.is_configured() is False

    @pytest.mark.asyncio
    async def test_create_unavailable_response_not_configured(self):
        """Test error response when broker not configured."""
        broker = MockBroker("testbroker")
        broker._auth_info.status = BrokerAuthStatus.NOT_CONFIGURED
        broker._auth_info.setup_instructions = "Set TEST_API_KEY environment variable"

        response = broker.create_unavailable_response("test operation")
        result = response["result"]

        assert "error" in result
        assert "testbroker" in result["error"].lower()
        assert "not configured" in result["error"].lower()
        assert result["status"] == "broker_unavailable"
        assert result["broker"] == "testbroker"
        assert result["auth_status"] == "not_configured"
        assert result["requires_setup"] is False  # No setup instructions trigger

    @pytest.mark.asyncio
    async def test_create_unavailable_response_auth_failed(self):
        """Test error response when authentication failed."""
        broker = MockBroker("testbroker")
        broker._auth_info.status = BrokerAuthStatus.AUTH_FAILED
        broker._auth_info.error_message = "Invalid API key"

        response = broker.create_unavailable_response("get account info")
        result = response["result"]

        assert "error" in result
        assert "Invalid API key" in result["error"]
        assert result["status"] == "broker_unavailable"
        assert result["auth_status"] == "auth_failed"

    @pytest.mark.asyncio
    async def test_create_unavailable_response_token_expired(self):
        """Test error response when token expired."""
        broker = MockBroker("testbroker")
        broker._auth_info.status = BrokerAuthStatus.TOKEN_EXPIRED

        response = broker.create_unavailable_response("place order")
        result = response["result"]

        assert "error" in result
        assert "session expired" in result["error"].lower()
        assert result["auth_status"] == "token_expired"

    @pytest.mark.asyncio
    async def test_auth_info_property(self):
        """Test auth_info property returns current state."""
        broker = MockBroker()
        auth_info = broker.auth_info

        assert isinstance(auth_info, BrokerAuthInfo)
        assert auth_info.status == BrokerAuthStatus.NOT_CONFIGURED

        # Modify state and check property reflects changes
        broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        assert broker.auth_info.status == BrokerAuthStatus.AUTHENTICATED

    @pytest.mark.asyncio
    async def test_multiple_authentication_attempts(self):
        """Test multiple authentication attempts update state correctly."""
        broker = MockBroker()

        # First attempt - fail
        broker._should_auth_succeed = False
        success1 = await broker.authenticate()
        assert success1 is False
        assert broker._auth_call_count == 1
        first_attempt_time = broker.auth_info.last_auth_attempt

        # Second attempt - succeed
        broker._should_auth_succeed = True
        success2 = await broker.authenticate()
        assert success2 is True
        assert broker._auth_call_count == 2
        assert broker.auth_info.last_auth_attempt > first_attempt_time
        assert broker.auth_info.last_successful_auth is not None
        assert broker.is_available()
