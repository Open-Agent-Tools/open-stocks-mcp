"""Integration tests for multi-broker functionality.

These tests verify that multiple brokers can work together correctly.
They use mocked broker responses to avoid requiring real credentials.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.brokers.auth_coordinator import (
    create_unauthenticated_tool_response,
)
from open_stocks_mcp.brokers.base import BrokerAuthStatus
from open_stocks_mcp.brokers.registry import BrokerRegistry, get_broker_registry
from open_stocks_mcp.brokers.robinhood import RobinhoodBroker
from open_stocks_mcp.brokers.schwab import SchwabBroker
from open_stocks_mcp.server.tool_helpers import (
    get_broker_status_data,
    get_list_brokers_data,
)
from tests.conftest import MockBroker


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
    @patch("schwab.auth")
    async def test_authenticate_all_brokers(
        self,
        mock_schwab_auth: MagicMock,
        mock_session_manager: MagicMock,
        registry: BrokerRegistry,
    ) -> None:
        """Test authenticating all brokers simultaneously."""
        # Mock Robinhood authentication
        mock_session = MagicMock()
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_session_manager.return_value = mock_session

        robinhood_broker = RobinhoodBroker(
            username="test@example.com",
            password="test_password",
        )

        # Mock Schwab authentication
        mock_schwab_client = MagicMock()
        mock_schwab_auth.easy_client.return_value = mock_schwab_client

        schwab_broker = SchwabBroker(
            api_key="test_api_key",
            app_secret="test_app_secret",
        )

        # Mock tty check to allow interactive auth mock
        with patch("os.isatty", return_value=True):
            registry.register(robinhood_broker)
            registry.register(schwab_broker)

            results = await registry.authenticate_all()

        assert results["robinhood"] is True
        assert results["schwab"] is True

    @pytest.mark.asyncio
    @patch("open_stocks_mcp.brokers.robinhood.SessionManager")
    @patch("schwab.auth")
    async def test_partial_authentication_failure(
        self,
        mock_schwab_auth: MagicMock,
        mock_session_manager: MagicMock,
        registry: BrokerRegistry,
    ) -> None:
        """Test handling when some brokers authenticate and others fail."""
        # Mock Robinhood authentication success
        mock_session = MagicMock()
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_session_manager.return_value = mock_session

        robinhood_broker = RobinhoodBroker(
            username="test@example.com",
            password="test_password",
        )

        # Mock Schwab authentication failure
        mock_schwab_auth.easy_client.side_effect = Exception("OAuth failed")

        schwab_broker = SchwabBroker(
            api_key="test_api_key",
            app_secret="test_app_secret",
        )

        # Mock tty check to allow interactive auth mock
        with patch("os.isatty", return_value=True):
            registry.register(robinhood_broker)
            registry.register(schwab_broker)

            results = await registry.authenticate_all()

        assert results["robinhood"] is True
        assert results["schwab"] is False

    def test_broker_not_found_error(self, registry: BrokerRegistry) -> None:
        """Test error when requesting non-existent broker."""
        assert registry.get_broker("nonexistent") is None

    def test_set_active_broker_not_registered(
        self, registry: BrokerRegistry, robinhood_broker: RobinhoodBroker
    ) -> None:
        """Test error when setting active broker that isn't registered."""
        registry.register(robinhood_broker)
        assert registry.set_active_broker("schwab") is False

    @pytest.mark.asyncio
    @patch("open_stocks_mcp.brokers.robinhood.SessionManager")
    async def test_broker_auth_status_tracking(
        self,
        mock_session_manager: MagicMock,
        registry: BrokerRegistry,
    ) -> None:
        """Test that broker authentication status is tracked correctly."""
        # Mock authentication
        mock_session = MagicMock()
        mock_session.ensure_authenticated = AsyncMock(return_value=True)
        mock_session.logout = AsyncMock()
        mock_session_manager.return_value = mock_session

        robinhood_broker = RobinhoodBroker(
            username="test@example.com",
            password="test_password",
        )

        registry.register(robinhood_broker)

        # Initially unauthenticated
        assert robinhood_broker.auth_info.status == BrokerAuthStatus.NOT_AUTHENTICATED

        # After authentication
        await robinhood_broker.authenticate()
        assert robinhood_broker.auth_info.status == BrokerAuthStatus.AUTHENTICATED

        # After logout
        await robinhood_broker.logout()
        assert robinhood_broker.auth_info.status == BrokerAuthStatus.NOT_AUTHENTICATED

    @pytest.mark.asyncio
    @patch("open_stocks_mcp.brokers.robinhood.SessionManager")
    @patch("schwab.auth")
    async def test_concurrent_broker_operations(
        self,
        mock_schwab_auth: MagicMock,
        mock_session_manager: MagicMock,
        registry: BrokerRegistry,
    ) -> None:
        """Test that multiple brokers can operate independently."""
        # Mock Robinhood
        mock_rh_session = MagicMock()
        mock_rh_session.ensure_authenticated = AsyncMock(return_value=True)

        # Track session validity state
        session_state = {"valid": True}

        def get_valid():
            return session_state["valid"]

        async def do_logout():
            session_state["valid"] = False

        mock_rh_session.is_session_valid.side_effect = get_valid
        mock_rh_session.logout = AsyncMock(side_effect=do_logout)
        mock_session_manager.return_value = mock_rh_session

        robinhood_broker = RobinhoodBroker(
            username="test@example.com",
            password="test_password",
        )

        # Mock Schwab
        mock_schwab_client = MagicMock()
        mock_schwab_auth.easy_client.return_value = mock_schwab_client

        schwab_broker = SchwabBroker(
            api_key="test_api_key",
            app_secret="test_app_secret",
        )

        # Mock tty check to allow interactive auth mock
        with patch("os.isatty", return_value=True):
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

    @pytest.mark.asyncio
    async def test_global_registry_singleton(self) -> None:
        """Test that get_broker_registry returns singleton instance."""
        registry1 = await get_broker_registry()
        registry2 = await get_broker_registry()

        # Should be the same instance
        assert registry1 is registry2

    @pytest.mark.asyncio
    @patch("schwab.auth")
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


@pytest.mark.asyncio
@pytest.mark.journey_system
class TestMultiBrokerStatusScenarios:
    """Integration-style status/list tests across broker configuration states."""

    async def test_broker_status_both_configured_authenticated(self) -> None:
        registry = BrokerRegistry()
        robinhood = MockBroker("robinhood", should_auth_succeed=True)
        schwab = MockBroker("schwab", should_auth_succeed=True)
        registry.register(robinhood)
        registry.register(schwab)
        await registry.authenticate_all()

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_broker_registry",
            return_value=registry,
        ):
            result = await get_broker_status_data()

        payload = result["result"]
        assert payload["total_configured"] == 2
        assert payload["total_authenticated"] == 2
        assert sorted(payload["available_brokers"]) == ["robinhood", "schwab"]
        assert payload["brokers"]["robinhood"]["status"] == "authenticated"
        assert payload["brokers"]["robinhood"]["is_available"] is True
        assert payload["brokers"]["schwab"]["status"] == "authenticated"
        assert payload["brokers"]["schwab"]["is_available"] is True

    async def test_list_brokers_both_configured_authenticated(self) -> None:
        registry = BrokerRegistry()
        robinhood = MockBroker("robinhood", should_auth_succeed=True)
        schwab = MockBroker("schwab", should_auth_succeed=True)
        registry.register(robinhood)
        registry.register(schwab)
        await registry.authenticate_all()

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_broker_registry",
            return_value=registry,
        ):
            result = await get_list_brokers_data()

        payload = result["result"]
        assert payload["count"] == 2
        broker_map = {entry["name"]: entry for entry in payload["brokers"]}
        assert broker_map["robinhood"]["available"] is True
        assert broker_map["robinhood"]["status"] == "authenticated"
        assert broker_map["robinhood"]["configured"] is True
        assert broker_map["schwab"]["available"] is True
        assert broker_map["schwab"]["status"] == "authenticated"
        assert broker_map["schwab"]["configured"] is True

    async def test_broker_status_only_robinhood_configured(self) -> None:
        registry = BrokerRegistry()
        robinhood = MockBroker("robinhood", should_auth_succeed=True)
        registry.register(robinhood)
        await registry.authenticate_all()

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_broker_registry",
            return_value=registry,
        ):
            result = await get_broker_status_data()

        payload = result["result"]
        assert payload["total_configured"] == 1
        assert payload["total_authenticated"] == 1
        assert payload["available_brokers"] == ["robinhood"]

    async def test_list_brokers_only_robinhood(self) -> None:
        registry = BrokerRegistry()
        robinhood = MockBroker("robinhood", should_auth_succeed=True)
        registry.register(robinhood)
        await registry.authenticate_all()

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_broker_registry",
            return_value=registry,
        ):
            result = await get_list_brokers_data()

        payload = result["result"]
        assert payload["count"] == 1
        assert payload["brokers"][0]["name"] == "robinhood"

    async def test_broker_status_only_schwab_configured(self) -> None:
        registry = BrokerRegistry()
        schwab = MockBroker("schwab", should_auth_succeed=True)
        registry.register(schwab)
        await registry.authenticate_all()

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_broker_registry",
            return_value=registry,
        ):
            result = await get_broker_status_data()

        payload = result["result"]
        assert payload["total_configured"] == 1
        assert payload["available_brokers"] == ["schwab"]

    async def test_list_brokers_only_schwab(self) -> None:
        registry = BrokerRegistry()
        schwab = MockBroker("schwab", should_auth_succeed=True)
        registry.register(schwab)
        await registry.authenticate_all()

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_broker_registry",
            return_value=registry,
        ):
            result = await get_list_brokers_data()

        payload = result["result"]
        assert payload["count"] == 1
        assert payload["brokers"][0]["name"] == "schwab"

    async def test_broker_status_neither_authenticated(self) -> None:
        registry = BrokerRegistry()
        robinhood = MockBroker("robinhood", should_auth_succeed=False)
        schwab = MockBroker("schwab", should_auth_succeed=False)
        registry.register(robinhood)
        registry.register(schwab)
        await registry.authenticate_all()

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_broker_registry",
            return_value=registry,
        ):
            result = await get_broker_status_data()

        payload = result["result"]
        assert payload["total_configured"] == 2
        assert payload["total_authenticated"] == 0
        assert payload["available_brokers"] == []
        assert payload["brokers"]["robinhood"]["is_available"] is False
        assert payload["brokers"]["robinhood"]["status"] == "auth_failed"
        assert payload["brokers"]["schwab"]["is_available"] is False
        assert payload["brokers"]["schwab"]["status"] == "auth_failed"

    async def test_list_brokers_neither_authenticated(self) -> None:
        registry = BrokerRegistry()
        robinhood = MockBroker("robinhood", should_auth_succeed=False)
        schwab = MockBroker("schwab", should_auth_succeed=False)
        registry.register(robinhood)
        registry.register(schwab)
        await registry.authenticate_all()

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_broker_registry",
            return_value=registry,
        ):
            result = await get_list_brokers_data()

        payload = result["result"]
        assert payload["count"] == 2
        broker_map = {entry["name"]: entry for entry in payload["brokers"]}
        assert broker_map["robinhood"]["available"] is False
        assert broker_map["schwab"]["available"] is False


@pytest.mark.asyncio
@pytest.mark.journey_system
class TestMultiBrokerErrorResponses:
    """Validate broker/tool error payloads for partial auth scenarios."""

    async def test_error_response_unavailable_broker_auth_failed(self) -> None:
        registry = BrokerRegistry()
        robinhood = MockBroker("robinhood", should_auth_succeed=True)
        schwab = MockBroker("schwab", should_auth_succeed=False)
        registry.register(robinhood)
        registry.register(schwab)
        await registry.authenticate_all()

        broker, error = registry.get_broker_or_error("schwab", "get_quote")
        assert broker is None
        assert error is not None
        result = error["result"]
        assert result["status"] == "broker_unavailable"
        assert result["broker"] == "schwab"
        assert result["auth_status"] == "auth_failed"

    async def test_error_response_unavailable_broker_not_configured(self) -> None:
        registry = BrokerRegistry()
        unconfigured = MockBroker(
            "unconfigured", should_auth_succeed=False, configured=False
        )
        registry.register(unconfigured)

        broker, error = registry.get_broker_or_error("unconfigured", "get_quote")
        assert broker is None
        assert error is not None
        result = error["result"]
        assert result["status"] == "broker_unavailable"
        assert result["auth_status"] == "not_configured"
        assert "environment variables" in result["error"]

    async def test_error_response_nonexistent_broker(self) -> None:
        registry = BrokerRegistry()
        broker, error = registry.get_broker_or_error("nonexistent", "get_quote")
        assert broker is None
        assert error is not None
        assert error["result"]["status"] == "broker_not_found"

    async def test_unauthenticated_tool_response_specific_broker(self) -> None:
        result = create_unauthenticated_tool_response("schwab")
        assert result["result"]["status"] == "no_authenticated_brokers"
        assert "Schwab" in result["result"]["error"]

    async def test_unauthenticated_tool_response_no_broker(self) -> None:
        result = create_unauthenticated_tool_response(None)
        assert result["result"]["status"] == "no_authenticated_brokers"
        assert "No authenticated brokers available" in result["result"]["error"]

    async def test_partial_auth_broker_status_shows_mixed_state(self) -> None:
        registry = BrokerRegistry()
        robinhood = MockBroker("robinhood", should_auth_succeed=True)
        schwab = MockBroker("schwab", should_auth_succeed=False)
        registry.register(robinhood)
        registry.register(schwab)
        await registry.authenticate_all()

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_broker_registry",
            return_value=registry,
        ):
            result = await get_broker_status_data()

        payload = result["result"]
        assert payload["total_authenticated"] == 1
        assert payload["brokers"]["robinhood"]["is_available"] is True
        assert payload["brokers"]["schwab"]["is_available"] is False
        assert payload["brokers"]["schwab"]["status"] == "auth_failed"
