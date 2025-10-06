"""Integration tests for multi-broker functionality.

These tests verify that multiple brokers can work together correctly.
They use mocked broker responses to avoid requiring real credentials.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.brokers.base import BrokerAuthStatus
from open_stocks_mcp.brokers.registry import BrokerRegistry, get_broker_registry
from open_stocks_mcp.brokers.robinhood import RobinhoodBroker
from open_stocks_mcp.brokers.schwab import SchwabBroker


class TestMultiBrokerIntegration:
    """Test multi-broker scenarios."""

    @pytest.fixture
    def registry(self) -> BrokerRegistry:
        """Create a fresh broker registry for testing."""
        # Create new registry instance
        registry = BrokerRegistry()
        return registry

    @pytest.fixture
    def robinhood_broker(self) -> RobinhoodBroker:
        """Create a Robinhood broker instance."""
        return RobinhoodBroker(
            username="test@example.com",
            password="test_password",
        )

    @pytest.fixture
    def schwab_broker(self) -> SchwabBroker:
        """Create a Schwab broker instance."""
        return SchwabBroker(
            api_key="test_api_key",
            app_secret="test_app_secret",
        )

    def test_register_multiple_brokers(
        self,
        registry: BrokerRegistry,
        robinhood_broker: RobinhoodBroker,
        schwab_broker: SchwabBroker,
    ) -> None:
        """Test registering multiple brokers."""
        registry.register(robinhood_broker)
        registry.register(schwab_broker)

        assert len(registry.list_brokers()) == 2
        assert "robinhood" in registry.list_brokers()
        assert "schwab" in registry.list_brokers()

    def test_get_broker_by_name(
        self,
        registry: BrokerRegistry,
        robinhood_broker: RobinhoodBroker,
        schwab_broker: SchwabBroker,
    ) -> None:
        """Test retrieving specific broker by name."""
        registry.register(robinhood_broker)
        registry.register(schwab_broker)

        rh = registry.get_broker("robinhood")
        assert rh.name == "robinhood"

        schwab = registry.get_broker("schwab")
        assert schwab.name == "schwab"

    def test_default_broker_selection(
        self,
        registry: BrokerRegistry,
        robinhood_broker: RobinhoodBroker,
    ) -> None:
        """Test that first registered broker becomes default."""
        registry.register(robinhood_broker)

        default = registry.get_broker()
        assert default.name == "robinhood"

    def test_switch_active_broker(
        self,
        registry: BrokerRegistry,
        robinhood_broker: RobinhoodBroker,
        schwab_broker: SchwabBroker,
    ) -> None:
        """Test switching between brokers."""
        registry.register(robinhood_broker)
        registry.register(schwab_broker)

        # Default is first registered (robinhood)
        assert registry.get_broker().name == "robinhood"

        # Switch to schwab
        registry.set_active_broker("schwab")
        assert registry.get_broker().name == "schwab"

        # Switch back to robinhood
        registry.set_active_broker("robinhood")
        assert registry.get_broker().name == "robinhood"

    @pytest.mark.asyncio
    @patch("open_stocks_mcp.brokers.robinhood.SessionManager")
    @patch("open_stocks_mcp.brokers.schwab.auth")
    async def test_authenticate_all_brokers(
        self,
        mock_schwab_auth: MagicMock,
        mock_session_manager: MagicMock,
        registry: BrokerRegistry,
        robinhood_broker: RobinhoodBroker,
        schwab_broker: SchwabBroker,
    ) -> None:
        """Test authenticating all brokers simultaneously."""
        # Mock Robinhood authentication
        mock_session = MagicMock()
        mock_session.ensure_authenticated.return_value = True
        mock_session_manager.return_value = mock_session

        # Mock Schwab authentication
        mock_schwab_client = MagicMock()
        mock_schwab_auth.easy_client.return_value = mock_schwab_client

        registry.register(robinhood_broker)
        registry.register(schwab_broker)

        results = await registry.authenticate_all()

        assert results["robinhood"] is True
        assert results["schwab"] is True

    @pytest.mark.asyncio
    @patch("open_stocks_mcp.brokers.robinhood.SessionManager")
    @patch("open_stocks_mcp.brokers.schwab.auth")
    async def test_partial_authentication_failure(
        self,
        mock_schwab_auth: MagicMock,
        mock_session_manager: MagicMock,
        registry: BrokerRegistry,
        robinhood_broker: RobinhoodBroker,
        schwab_broker: SchwabBroker,
    ) -> None:
        """Test handling when some brokers authenticate and others fail."""
        # Mock Robinhood authentication success
        mock_session = MagicMock()
        mock_session.ensure_authenticated.return_value = True
        mock_session_manager.return_value = mock_session

        # Mock Schwab authentication failure
        mock_schwab_auth.easy_client.side_effect = Exception("OAuth failed")

        registry.register(robinhood_broker)
        registry.register(schwab_broker)

        results = await registry.authenticate_all()

        assert results["robinhood"] is True
        assert results["schwab"] is False

    def test_broker_not_found_error(self, registry: BrokerRegistry) -> None:
        """Test error when requesting non-existent broker."""
        with pytest.raises(ValueError, match="Broker not found"):
            registry.get_broker("nonexistent")

    def test_set_active_broker_not_registered(
        self, registry: BrokerRegistry, robinhood_broker: RobinhoodBroker
    ) -> None:
        """Test error when setting active broker that isn't registered."""
        registry.register(robinhood_broker)

        with pytest.raises(ValueError, match="Broker not registered"):
            registry.set_active_broker("schwab")

    @pytest.mark.asyncio
    @patch("open_stocks_mcp.brokers.robinhood.SessionManager")
    async def test_broker_auth_status_tracking(
        self,
        mock_session_manager: MagicMock,
        registry: BrokerRegistry,
        robinhood_broker: RobinhoodBroker,
    ) -> None:
        """Test that broker authentication status is tracked correctly."""
        # Mock authentication
        mock_session = MagicMock()
        mock_session.ensure_authenticated.return_value = True
        mock_session_manager.return_value = mock_session

        registry.register(robinhood_broker)

        # Initially unauthenticated
        assert robinhood_broker.auth_status == BrokerAuthStatus.UNAUTHENTICATED

        # After authentication
        await robinhood_broker.authenticate()
        assert robinhood_broker.auth_status == BrokerAuthStatus.AUTHENTICATED

        # After logout
        await robinhood_broker.logout()
        assert robinhood_broker.auth_status == BrokerAuthStatus.UNAUTHENTICATED

    @pytest.mark.asyncio
    @patch("open_stocks_mcp.brokers.robinhood.SessionManager")
    @patch("open_stocks_mcp.brokers.schwab.auth")
    async def test_concurrent_broker_operations(
        self,
        mock_schwab_auth: MagicMock,
        mock_session_manager: MagicMock,
        registry: BrokerRegistry,
        robinhood_broker: RobinhoodBroker,
        schwab_broker: SchwabBroker,
    ) -> None:
        """Test that multiple brokers can operate independently."""
        # Mock Robinhood
        mock_rh_session = MagicMock()
        mock_rh_session.ensure_authenticated.return_value = True
        mock_session_manager.return_value = mock_rh_session

        # Mock Schwab
        mock_schwab_client = MagicMock()
        mock_schwab_auth.easy_client.return_value = mock_schwab_client

        registry.register(robinhood_broker)
        registry.register(schwab_broker)

        # Authenticate both
        await registry.authenticate_all()

        # Verify both are authenticated
        rh = registry.get_broker("robinhood")
        assert await rh.is_authenticated()

        schwab = registry.get_broker("schwab")
        assert await schwab.is_authenticated()

        # Logout one, verify other still authenticated
        await rh.logout()
        assert not await rh.is_authenticated()
        assert await schwab.is_authenticated()

    def test_global_registry_singleton(self) -> None:
        """Test that get_broker_registry returns singleton instance."""
        registry1 = get_broker_registry()
        registry2 = get_broker_registry()

        # Should be the same instance
        assert registry1 is registry2

    @pytest.mark.asyncio
    @patch("open_stocks_mcp.brokers.schwab.auth")
    async def test_schwab_token_persistence(
        self, mock_schwab_auth: MagicMock, schwab_broker: SchwabBroker, tmp_path
    ) -> None:
        """Test that Schwab tokens persist across sessions."""
        # Create token file
        token_file = tmp_path / "schwab_token.json"
        token_file.write_text('{"access_token": "test_token"}')
        schwab_broker.token_path = str(token_file)

        # Mock client from token file
        mock_client = MagicMock()
        mock_schwab_auth.client_from_token_file.return_value = mock_client

        # Authenticate
        result = await schwab_broker.authenticate()

        assert result is True
        assert schwab_broker.client is not None
        # Should use existing token, not easy_client
        mock_schwab_auth.client_from_token_file.assert_called_once()
        mock_schwab_auth.easy_client.assert_not_called()
