"""Unit tests for broker registry management."""

import asyncio
from datetime import datetime

import pytest

from open_stocks_mcp.brokers.base import BaseBroker, BrokerAuthStatus
from open_stocks_mcp.brokers.registry import (
    BrokerRegistry,
    RegistryNotInitializedError,
    get_broker_registry,
    get_broker_registry_sync,
)
from open_stocks_mcp.monitoring import MetricsCollector


class MockBroker(BaseBroker):
    """Mock broker for testing registry."""

    def __init__(
        self, name: str, should_auth_succeed: bool = True, configured: bool = True
    ):
        super().__init__(name)
        self._should_auth_succeed = should_auth_succeed
        self._auth_call_count = 0
        self._logout_call_count = 0

        # Set configured status
        if configured:
            self._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED
        else:
            self._auth_info.status = BrokerAuthStatus.NOT_CONFIGURED

    async def authenticate(self) -> bool:
        """Mock authentication."""
        self._auth_call_count += 1
        self._auth_info.last_auth_attempt = datetime.now()

        if self._should_auth_succeed:
            self._auth_info.status = BrokerAuthStatus.AUTHENTICATED
            self._auth_info.last_successful_auth = datetime.now()
            return True
        else:
            self._auth_info.status = BrokerAuthStatus.AUTH_FAILED
            self._auth_info.error_message = "Mock auth failed"
            return False

    async def is_authenticated(self) -> bool:
        return self._auth_info.status == BrokerAuthStatus.AUTHENTICATED

    async def logout(self) -> None:
        self._logout_call_count += 1
        self._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED

    # Required abstract method implementations
    async def get_account_info(self):
        return {"result": {"mock": "account"}}

    async def get_portfolio(self):
        return {"result": {"mock": "portfolio"}}

    async def get_positions(self):
        return {"result": {"mock": "positions"}}

    async def get_stock_quote(self, symbol: str):
        return {"result": {"price": 100}}

    async def get_stock_price(self, symbol: str):
        return {"result": {"price": 100}}

    async def order_buy_market(self, symbol: str, quantity: float):
        return {"result": {"order": "buy"}}

    async def order_sell_market(self, symbol: str, quantity: float):
        return {"result": {"order": "sell"}}


class TestBrokerRegistry:
    """Test BrokerRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return BrokerRegistry()

    @pytest.mark.asyncio
    async def test_registry_initialization(self, registry):
        """Test registry initializes empty."""
        assert len(registry.list_brokers()) == 0
        assert len(registry.get_available_brokers()) == 0

    @pytest.mark.asyncio
    async def test_register_single_broker(self, registry):
        """Test registering a single broker."""
        broker = MockBroker("test1")
        registry.register(broker)

        brokers = registry.list_brokers()
        assert len(brokers) == 1
        assert "test1" in brokers

    @pytest.mark.asyncio
    async def test_register_multiple_brokers(self, registry):
        """Test registering multiple brokers."""
        broker1 = MockBroker("broker1")
        broker2 = MockBroker("broker2")
        broker3 = MockBroker("broker3")

        registry.register(broker1)
        registry.register(broker2)
        registry.register(broker3)

        brokers = registry.list_brokers()
        assert len(brokers) == 3
        assert "broker1" in brokers
        assert "broker2" in brokers
        assert "broker3" in brokers

    @pytest.mark.asyncio
    async def test_register_duplicate_broker_overwrites(self, registry):
        """Test registering duplicate broker name overwrites previous."""
        broker1 = MockBroker("duplicate")
        broker2 = MockBroker("duplicate")

        registry.register(broker1)
        registry.register(broker2)  # Should overwrite

        # Should have the second broker
        assert registry.get_broker("duplicate") is broker2

    @pytest.mark.asyncio
    async def test_get_broker_exists(self, registry):
        """Test getting an existing broker."""
        broker = MockBroker("test")
        registry.register(broker)

        retrieved = registry.get_broker("test")
        assert retrieved is broker
        assert retrieved.name == "test"

    @pytest.mark.asyncio
    async def test_get_broker_not_exists(self, registry):
        """Test getting non-existent broker returns None."""
        retrieved = registry.get_broker("nonexistent")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_authenticate_all_success(self, registry):
        """Test authenticate_all with all successful authentications."""
        broker1 = MockBroker("broker1", should_auth_succeed=True)
        broker2 = MockBroker("broker2", should_auth_succeed=True)

        registry.register(broker1)
        registry.register(broker2)

        results = await registry.authenticate_all()

        assert len(results) == 2
        # Results dict values should all be True after auth succeeds
        assert all(results.values())
        assert broker1._auth_call_count >= 1
        assert broker2._auth_call_count >= 1

    @pytest.mark.asyncio
    async def test_authenticate_all_partial_success(self, registry):
        """Test authenticate_all with partial success."""
        broker1 = MockBroker("broker1", should_auth_succeed=True)
        broker2 = MockBroker("broker2", should_auth_succeed=False)
        broker3 = MockBroker("broker3", should_auth_succeed=True)

        registry.register(broker1)
        registry.register(broker2)
        registry.register(broker3)

        results = await registry.authenticate_all()

        assert len(results) == 3
        # Check that we have mix of success and failure
        successes = sum(1 for v in results.values() if v)
        assert successes == 2  # Two should succeed

    @pytest.mark.asyncio
    async def test_authenticate_all_all_fail(self, registry):
        """Test authenticate_all with all failures."""
        broker1 = MockBroker("broker1", should_auth_succeed=False)
        broker2 = MockBroker("broker2", should_auth_succeed=False)

        registry.register(broker1)
        registry.register(broker2)

        results = await registry.authenticate_all()

        assert results["broker1"] is False
        assert results["broker2"] is False

    @pytest.mark.asyncio
    async def test_authenticate_all_empty_registry(self, registry):
        """Test authenticate_all with no brokers registered."""
        results = await registry.authenticate_all()
        assert results == {}

    @pytest.mark.asyncio
    async def test_get_available_brokers_all_authenticated(self, registry):
        """Test get_available_brokers with all authenticated."""
        broker1 = MockBroker("broker1", should_auth_succeed=True)
        broker2 = MockBroker("broker2", should_auth_succeed=True)

        registry.register(broker1)
        registry.register(broker2)
        await registry.authenticate_all()

        available = registry.get_available_brokers()
        assert len(available) == 2
        assert "broker1" in available
        assert "broker2" in available

    @pytest.mark.asyncio
    async def test_get_available_brokers_partial_auth(self, registry):
        """Test get_available_brokers with partial authentication."""
        broker1 = MockBroker("broker1", should_auth_succeed=True)
        broker2 = MockBroker("broker2", should_auth_succeed=False)

        registry.register(broker1)
        registry.register(broker2)
        await registry.authenticate_all()

        available = registry.get_available_brokers()
        assert len(available) == 1
        assert "broker1" in available
        assert "broker2" not in available

    @pytest.mark.asyncio
    async def test_get_available_brokers_none_authenticated(self, registry):
        """Test get_available_brokers with no authentication."""
        broker1 = MockBroker("broker1", should_auth_succeed=False)
        broker2 = MockBroker("broker2", should_auth_succeed=False)

        registry.register(broker1)
        registry.register(broker2)
        await registry.authenticate_all()

        available = registry.get_available_brokers()
        assert len(available) == 0

    @pytest.mark.asyncio
    async def test_get_broker_or_error_available(self, registry):
        """Test get_broker_or_error returns broker when available."""
        broker = MockBroker("test", should_auth_succeed=True)
        registry.register(broker)
        await broker.authenticate()

        result_broker, error = registry.get_broker_or_error("test", "test operation")

        assert result_broker is broker
        assert error is None

    @pytest.mark.asyncio
    async def test_get_broker_or_error_not_available(self, registry):
        """Test get_broker_or_error returns error when unavailable."""
        broker = MockBroker("test", should_auth_succeed=False)
        registry.register(broker)
        await broker.authenticate()

        result_broker, error = registry.get_broker_or_error("test", "test operation")

        assert result_broker is None
        assert error is not None
        assert "result" in error
        assert "error" in error["result"]

    @pytest.mark.asyncio
    async def test_get_broker_or_error_not_registered(self, registry):
        """Test get_broker_or_error with non-existent broker."""
        result_broker, error = registry.get_broker_or_error(
            "nonexistent", "test operation"
        )

        assert result_broker is None
        assert error is not None
        assert "result" in error
        assert "error" in error["result"]
        assert "not found" in error["result"]["error"].lower()

    @pytest.mark.asyncio
    async def test_get_auth_status_all_brokers(self, registry):
        """Test get_auth_status returns status for all brokers."""
        broker1 = MockBroker("broker1", should_auth_succeed=True)
        broker2 = MockBroker("broker2", should_auth_succeed=False)

        registry.register(broker1)
        registry.register(broker2)
        await registry.authenticate_all()

        status = registry.get_auth_status()

        assert "broker1" in status
        assert "broker2" in status
        # broker1 should be authenticated after successful auth
        assert status["broker1"]["is_available"] is True
        # broker2 should have failed auth
        assert status["broker2"]["is_available"] is False

    @pytest.mark.asyncio
    async def test_get_auth_status_includes_timestamps(self, registry):
        """Test get_auth_status includes timestamp information."""
        broker = MockBroker("test", should_auth_succeed=True)
        registry.register(broker)
        await broker.authenticate()

        status = registry.get_auth_status()

        assert "test" in status
        assert "last_auth_attempt" in status["test"]
        assert "last_successful_auth" in status["test"]
        assert status["test"]["last_auth_attempt"] is not None
        assert status["test"]["last_successful_auth"] is not None

    @pytest.mark.asyncio
    async def test_set_active_broker(self, registry):
        """Test setting active broker."""
        broker1 = MockBroker("broker1")
        broker2 = MockBroker("broker2")

        registry.register(broker1)
        registry.register(broker2)

        # Set active broker
        result = registry.set_active_broker("broker1")
        assert result is True

        # Verify active broker
        active = registry.get_broker(None)  # None gets active
        assert active is broker1

        # Change active broker
        result = registry.set_active_broker("broker2")
        assert result is True
        active = registry.get_broker(None)
        assert active is broker2

    @pytest.mark.asyncio
    async def test_set_active_broker_nonexistent(self, registry):
        """Test setting active broker to non-existent name returns False."""
        result = registry.set_active_broker("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_concurrent_operations_bound_fanout_and_isolate_timeout(
        self, registry, monkeypatch: pytest.MonkeyPatch
    ):
        """Concurrent broker execution should bound fan-out and isolate failures."""
        monkeypatch.setattr(
            "open_stocks_mcp.monitoring._metrics_collector", MetricsCollector()
        )
        active = 0
        max_active = 0

        async def tracked_result(value: str, delay: float = 0.01) -> dict[str, str]:
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            try:
                await asyncio.sleep(delay)
                return {"value": value}
            finally:
                active -= 1

        operations = [
            {
                "broker": "robinhood",
                "account_id": "acct-1",
                "operation": "quote",
                "call": lambda: tracked_result("rh"),
            },
            {
                "broker": "schwab",
                "account_id": "acct-2",
                "operation": "quote",
                "call": lambda: tracked_result("schwab", delay=0.2),
            },
            {
                "broker": "robinhood",
                "account_id": "acct-3",
                "operation": "quote",
                "call": lambda: tracked_result("rh-2"),
            },
        ]

        results = await registry.run_concurrent_operations(
            operations, concurrency_limit=2, timeout_seconds=0.05
        )

        assert max_active <= 2
        assert len(results) == 3
        assert results[0]["broker"] == "robinhood"
        assert results[0]["account_id"] == "acct-1"
        assert results[0]["operation"] == "quote"
        assert results[0]["status"] == "success"
        assert results[0]["result"] == {"value": "rh"}
        assert results[1]["status"] == "timeout"
        assert results[1]["error"]["failure_class"] == "timeout"
        assert results[2]["status"] == "success"

    @pytest.mark.asyncio
    async def test_auth_refresh_single_flight_is_per_broker_account(self, registry):
        """Concurrent refreshes should coalesce per broker/account key."""
        refresh_count = 0

        async def refresh() -> bool:
            nonlocal refresh_count
            refresh_count += 1
            await asyncio.sleep(0.01)
            return True

        tasks = [
            registry.coordinate_auth_refresh("robinhood", "acct-1", refresh)
            for _ in range(20)
        ]
        tasks.append(registry.coordinate_auth_refresh("robinhood", "acct-2", refresh))

        results = await asyncio.gather(*tasks)

        assert all(results)
        assert refresh_count == 2


class TestBrokerRegistrySingleton:
    """Test get_broker_registry singleton pattern."""

    @pytest.mark.asyncio
    async def test_get_broker_registry_returns_instance(self):
        """Test get_broker_registry returns BrokerRegistry instance."""
        registry = await get_broker_registry()
        assert isinstance(registry, BrokerRegistry)

    @pytest.mark.asyncio
    async def test_get_broker_registry_returns_same_instance(self):
        """Test get_broker_registry returns same instance (singleton)."""
        registry1 = await get_broker_registry()
        registry2 = await get_broker_registry()
        assert registry1 is registry2

    @pytest.mark.asyncio
    async def test_singleton_persists_registered_brokers(self):
        """Test singleton registry persists brokers across calls."""
        registry1 = await get_broker_registry()
        broker = MockBroker("persistent")
        registry1.register(broker)

        registry2 = await get_broker_registry()
        assert "persistent" in registry2.list_brokers()
        assert registry2.get_broker("persistent") is broker

    def test_get_broker_registry_sync_uninitialized(self):
        """Test get_broker_registry_sync raises RegistryNotInitializedError when uninitialized."""
        import open_stocks_mcp.brokers.registry as registry_mod

        # Ensure it's uninitialized for this test
        original_registry = registry_mod._registry
        registry_mod._registry = None

        try:
            with pytest.raises(RegistryNotInitializedError):
                get_broker_registry_sync()
        finally:
            # Restore original state
            registry_mod._registry = original_registry
