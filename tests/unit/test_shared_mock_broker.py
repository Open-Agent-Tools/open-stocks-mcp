"""Tests for the shared MockBroker helper in tests.conftest."""

import pytest

from open_stocks_mcp.brokers.base import BrokerAuthStatus
from tests.conftest import MockBroker


class TestMockBrokerSuccessfulAuth:
    """MockBroker correctly handles successful authentication."""

    @pytest.mark.asyncio
    async def test_successful_auth_sets_authenticated_status(self):
        broker = MockBroker("test", should_auth_succeed=True)
        result = await broker.authenticate()
        assert result is True
        assert broker._auth_info.status == BrokerAuthStatus.AUTHENTICATED

    @pytest.mark.asyncio
    async def test_successful_auth_sets_timestamps(self):
        broker = MockBroker("test", should_auth_succeed=True)
        await broker.authenticate()
        assert broker._auth_info.last_auth_attempt is not None
        assert broker._auth_info.last_successful_auth is not None

    @pytest.mark.asyncio
    async def test_successful_auth_increments_call_count(self):
        broker = MockBroker("test", should_auth_succeed=True)
        await broker.authenticate()
        await broker.authenticate()
        assert broker._auth_call_count == 2


class TestMockBrokerFailedAuth:
    """MockBroker correctly handles authentication failure."""

    @pytest.mark.asyncio
    async def test_failed_auth_returns_false(self):
        broker = MockBroker("test", should_auth_succeed=False)
        result = await broker.authenticate()
        assert result is False

    @pytest.mark.asyncio
    async def test_failed_auth_sets_auth_failed_status(self):
        broker = MockBroker("test", should_auth_succeed=False)
        await broker.authenticate()
        assert broker._auth_info.status == BrokerAuthStatus.AUTH_FAILED

    @pytest.mark.asyncio
    async def test_failed_auth_sets_error_message(self):
        broker = MockBroker("test", should_auth_succeed=False)
        await broker.authenticate()
        assert broker._auth_info.error_message is not None
        assert len(broker._auth_info.error_message) > 0

    @pytest.mark.asyncio
    async def test_failed_auth_sets_attempt_timestamp(self):
        broker = MockBroker("test", should_auth_succeed=False)
        await broker.authenticate()
        assert broker._auth_info.last_auth_attempt is not None


class TestMockBrokerUnconfigured:
    """MockBroker initializes to NOT_CONFIGURED when configured=False."""

    @pytest.mark.asyncio
    async def test_unconfigured_starts_not_configured(self):
        broker = MockBroker("test", configured=False)
        assert broker._auth_info.status == BrokerAuthStatus.NOT_CONFIGURED

    @pytest.mark.asyncio
    async def test_configured_starts_not_authenticated(self):
        broker = MockBroker("test", configured=True)
        assert broker._auth_info.status == BrokerAuthStatus.NOT_AUTHENTICATED


class TestMockBrokerAuthDelay:
    """MockBroker respects auth_delay parameter."""

    @pytest.mark.asyncio
    async def test_auth_delay_completes(self):
        broker = MockBroker("test", should_auth_succeed=True, auth_delay=0.01)
        result = await broker.authenticate()
        assert result is True
        assert broker._auth_info.status == BrokerAuthStatus.AUTHENTICATED

    @pytest.mark.asyncio
    async def test_zero_delay_still_authenticates(self):
        broker = MockBroker("test", should_auth_succeed=True, auth_delay=0)
        result = await broker.authenticate()
        assert result is True


class TestMockBrokerLogout:
    """MockBroker logout resets status and tracks count."""

    @pytest.mark.asyncio
    async def test_logout_resets_status_to_not_authenticated(self):
        broker = MockBroker("test", should_auth_succeed=True)
        await broker.authenticate()
        assert broker._auth_info.status == BrokerAuthStatus.AUTHENTICATED
        await broker.logout()
        assert broker._auth_info.status == BrokerAuthStatus.NOT_AUTHENTICATED

    @pytest.mark.asyncio
    async def test_logout_increments_count(self):
        broker = MockBroker("test")
        await broker.logout()
        await broker.logout()
        assert broker._logout_call_count == 2

    @pytest.mark.asyncio
    async def test_logout_count_starts_at_zero(self):
        broker = MockBroker("test")
        assert broker._logout_call_count == 0
