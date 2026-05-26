"""Unit tests for authentication coordinator."""

from unittest.mock import patch

import pytest

from open_stocks_mcp.brokers.auth_coordinator import (
    attempt_broker_logins,
    create_unauthenticated_tool_response,
    get_authenticated_broker_or_error,
)
from open_stocks_mcp.brokers.base import BrokerAuthStatus
from open_stocks_mcp.brokers.registry import BrokerRegistry
from tests.conftest import MockBroker


@pytest.fixture
async def fresh_registry():
    """Create a fresh registry for each test."""
    # Create new registry instance
    registry = BrokerRegistry()

    # Patch the singleton to return our fresh instance
    with patch(
        "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
        return_value=registry,
    ):
        yield registry


class TestAttemptBrokerLogins:
    """Test attempt_broker_logins coordinator function."""

    @pytest.mark.asyncio
    async def test_no_brokers_registered(self, fresh_registry):
        """Test with no brokers registered."""
        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            successful, total, failed = await attempt_broker_logins()

        assert successful == 0
        assert total == 0
        assert failed == []

    @pytest.mark.asyncio
    async def test_single_broker_success(self, fresh_registry):
        """Test with single broker authenticating successfully."""
        broker = MockBroker("test", should_auth_succeed=True)
        fresh_registry.register(broker)

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            successful, total, failed = await attempt_broker_logins()

        assert successful == 1
        assert total == 1
        assert failed == []
        assert broker._auth_call_count == 1

    @pytest.mark.asyncio
    async def test_single_broker_failure(self, fresh_registry):
        """Test with single broker authentication failure."""
        broker = MockBroker("test", should_auth_succeed=False)
        fresh_registry.register(broker)

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            successful, total, failed = await attempt_broker_logins()

        assert successful == 0
        assert total == 1
        assert failed == ["test"]

    @pytest.mark.asyncio
    async def test_multiple_brokers_all_success(self, fresh_registry):
        """Test with multiple brokers all succeeding."""
        broker1 = MockBroker("broker1", should_auth_succeed=True)
        broker2 = MockBroker("broker2", should_auth_succeed=True)
        broker3 = MockBroker("broker3", should_auth_succeed=True)

        fresh_registry.register(broker1)
        fresh_registry.register(broker2)
        fresh_registry.register(broker3)

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            successful, total, failed = await attempt_broker_logins()

        assert successful == 3
        assert total == 3
        assert failed == []

    @pytest.mark.asyncio
    async def test_multiple_brokers_partial_success(self, fresh_registry):
        """Test with partial authentication success."""
        broker1 = MockBroker("broker1", should_auth_succeed=True)
        broker2 = MockBroker("broker2", should_auth_succeed=False)
        broker3 = MockBroker("broker3", should_auth_succeed=True)

        fresh_registry.register(broker1)
        fresh_registry.register(broker2)
        fresh_registry.register(broker3)

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            successful, total, failed = await attempt_broker_logins()

        assert successful == 2
        assert total == 3
        assert failed == ["broker2"]

    @pytest.mark.asyncio
    async def test_multiple_brokers_all_fail(self, fresh_registry):
        """Test with all brokers failing authentication."""
        broker1 = MockBroker("broker1", should_auth_succeed=False)
        broker2 = MockBroker("broker2", should_auth_succeed=False)

        fresh_registry.register(broker1)
        fresh_registry.register(broker2)

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            successful, total, failed = await attempt_broker_logins()

        assert successful == 0
        assert total == 2
        assert failed == ["broker1", "broker2"]

    @pytest.mark.asyncio
    async def test_require_at_least_one_flag(self, fresh_registry):
        """Test require_at_least_one flag (mainly for logging)."""
        broker = MockBroker("test", should_auth_succeed=False)
        fresh_registry.register(broker)

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            # Should not raise error even with require_at_least_one=True
            successful, total, failed = await attempt_broker_logins(
                require_at_least_one=True
            )

        assert successful == 0
        assert total == 1
        assert failed == ["test"]

    @pytest.mark.asyncio
    async def test_broker_not_configured_status(self, fresh_registry):
        """Test handling of NOT_CONFIGURED status."""
        broker = MockBroker("test", should_auth_succeed=False)
        broker._auth_info.status = BrokerAuthStatus.NOT_CONFIGURED
        fresh_registry.register(broker)

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            successful, total, failed = await attempt_broker_logins()

        assert successful == 0
        assert total == 1
        assert "test" in failed

    @pytest.mark.asyncio
    async def test_broker_mfa_required_status(self, fresh_registry):
        """Test handling of MFA_REQUIRED status."""
        broker = MockBroker("test", should_auth_succeed=False)
        broker._auth_info.status = BrokerAuthStatus.MFA_REQUIRED
        fresh_registry.register(broker)

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            successful, total, failed = await attempt_broker_logins()

        assert successful == 0
        assert total == 1
        assert "test" in failed


class TestCreateUnauthenticatedToolResponse:
    """Test create_unauthenticated_tool_response helper."""

    def test_response_with_broker_name(self):
        """Test error response with specific broker name."""
        response = create_unauthenticated_tool_response("robinhood")

        assert "result" in response
        result = response["result"]
        assert "error" in result
        assert "robinhood" in result["error"].lower()
        assert result["status"] == "no_authenticated_brokers"
        assert "help" in result

    def test_response_without_broker_name(self):
        """Test error response without specific broker."""
        response = create_unauthenticated_tool_response()

        assert "result" in response
        result = response["result"]
        assert "error" in result
        assert "no authenticated brokers" in result["error"].lower()
        assert result["status"] == "no_authenticated_brokers"

    def test_response_includes_help_text(self):
        """Test response includes helpful guidance."""
        response = create_unauthenticated_tool_response("test")

        result = response["result"]
        assert "help" in result
        assert "broker_status" in result["help"]


class TestGetAuthenticatedBrokerOrError:
    """Test get_authenticated_broker_or_error helper."""

    @pytest.mark.asyncio
    async def test_get_available_broker(self, fresh_registry):
        """Test getting available authenticated broker."""
        broker = MockBroker("test", should_auth_succeed=True)
        fresh_registry.register(broker)
        await broker.authenticate()

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            result_broker, error = await get_authenticated_broker_or_error("test")

        assert result_broker is broker
        assert error is None

    @pytest.mark.asyncio
    async def test_get_unavailable_broker(self, fresh_registry):
        """Test getting unavailable broker returns error."""
        broker = MockBroker("test", should_auth_succeed=False)
        fresh_registry.register(broker)
        await broker.authenticate()

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            result_broker, error = await get_authenticated_broker_or_error("test")

        assert result_broker is None
        assert error is not None
        assert "result" in error
        assert "error" in error["result"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_broker(self, fresh_registry):
        """Test getting non-existent broker returns error."""
        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            result_broker, error = await get_authenticated_broker_or_error(
                "nonexistent"
            )

        assert result_broker is None
        assert error is not None

    @pytest.mark.asyncio
    async def test_operation_parameter_in_error(self, fresh_registry):
        """Test operation parameter is included in error message."""
        broker = MockBroker("test", should_auth_succeed=False)
        fresh_registry.register(broker)
        await broker.authenticate()

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            _, error = await get_authenticated_broker_or_error(
                "test", operation="get portfolio"
            )

        # Error response should reference the operation
        assert error is not None
        assert "result" in error

    @pytest.mark.asyncio
    async def test_none_broker_name_uses_active(self, fresh_registry):
        """Test passing None uses active broker."""
        broker = MockBroker("active", should_auth_succeed=True)
        fresh_registry.register(broker)
        fresh_registry.set_active_broker("active")
        await broker.authenticate()

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            result_broker, error = await get_authenticated_broker_or_error(None)

        # Should get the active broker
        assert result_broker is broker or error is not None


class TestAuthenticationIntegrationScenarios:
    """Integration-style tests for complete authentication flows."""

    @pytest.mark.asyncio
    async def test_complete_startup_flow_all_success(self, fresh_registry):
        """Test complete server startup with all brokers succeeding."""
        # Setup brokers
        robinhood = MockBroker("robinhood", should_auth_succeed=True)
        schwab = MockBroker("schwab", should_auth_succeed=True)

        fresh_registry.register(robinhood)
        fresh_registry.register(schwab)

        # Attempt logins (simulates server startup)
        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            successful, total, failed = await attempt_broker_logins()

        # Verify startup succeeded
        assert successful == 2
        assert total == 2
        assert failed == []

        # Verify tools can access brokers
        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            broker1, err1 = await get_authenticated_broker_or_error("robinhood")
            broker2, err2 = await get_authenticated_broker_or_error("schwab")

        assert broker1 is robinhood
        assert err1 is None
        assert broker2 is schwab
        assert err2 is None

    @pytest.mark.asyncio
    async def test_complete_startup_flow_partial_success(self, fresh_registry):
        """Test server startup with partial authentication (graceful degradation)."""
        # Setup brokers - one fails
        robinhood = MockBroker("robinhood", should_auth_succeed=True)
        schwab = MockBroker("schwab", should_auth_succeed=False)

        fresh_registry.register(robinhood)
        fresh_registry.register(schwab)

        # Attempt logins - should not crash
        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            successful, total, failed = await attempt_broker_logins()

        # Verify partial success
        assert successful == 1
        assert total == 2
        assert failed == ["schwab"]

        # Verify working broker still accessible
        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            broker1, err1 = await get_authenticated_broker_or_error("robinhood")
            broker2, err2 = await get_authenticated_broker_or_error("schwab")

        assert broker1 is robinhood
        assert err1 is None
        assert broker2 is None
        assert err2 is not None

    @pytest.mark.asyncio
    async def test_complete_startup_flow_all_fail(self, fresh_registry):
        """Test server startup with all authentications failing (still starts)."""
        # Setup brokers - all fail
        robinhood = MockBroker("robinhood", should_auth_succeed=False)
        schwab = MockBroker("schwab", should_auth_succeed=False)

        fresh_registry.register(robinhood)
        fresh_registry.register(schwab)

        # Attempt logins - should not crash server
        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            successful, total, failed = await attempt_broker_logins()

        # Verify server "started" even with no auth
        assert successful == 0
        assert total == 2
        assert failed == ["robinhood", "schwab"]

        # Verify tools return appropriate errors
        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            broker1, err1 = await get_authenticated_broker_or_error("robinhood")
            broker2, err2 = await get_authenticated_broker_or_error("schwab")

        assert broker1 is None
        assert err1 is not None
        assert broker2 is None
        assert err2 is not None

    @pytest.mark.asyncio
    async def test_complete_startup_flow_no_brokers(self, fresh_registry):
        """Test server startup with no brokers configured."""
        # No brokers registered

        # Attempt logins - should handle gracefully
        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            successful, total, failed = await attempt_broker_logins()

        # Verify graceful handling
        assert successful == 0
        assert total == 0
        assert failed == []


class TestAuthFailedStructuredResponse:
    """Tests that auth failure produces structured broker_unavailable responses."""

    @pytest.mark.asyncio
    async def test_get_broker_or_error_returns_auth_failed_status(self, fresh_registry):
        """Broker with AUTH_FAILED status returns structured response with auth_status='auth_failed'."""
        broker = MockBroker("test", should_auth_succeed=False)
        fresh_registry.register(broker)
        await broker.authenticate()  # sets AUTH_FAILED

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            result_broker, error = await get_authenticated_broker_or_error(
                "test", "get quote"
            )

        assert result_broker is None
        assert error is not None
        result = error["result"]
        assert result["status"] == "broker_unavailable"
        assert result["auth_status"] == "auth_failed"
        assert result["broker"] == "test"

    @pytest.mark.asyncio
    async def test_invalid_credentials_produces_structured_error(self, fresh_registry):
        """Broker whose authenticate() returns False gives a structured, non-raising error."""
        broker = MockBroker("robinhood", should_auth_succeed=False)
        fresh_registry.register(broker)
        await broker.authenticate()

        with patch(
            "open_stocks_mcp.brokers.auth_coordinator.get_broker_registry",
            return_value=fresh_registry,
        ):
            _, error = await get_authenticated_broker_or_error(
                "robinhood", "get account info"
            )

        assert error is not None
        result = error["result"]
        assert "error" in result
        assert "robinhood" in result["error"].lower()
        assert result["auth_status"] == "auth_failed"
