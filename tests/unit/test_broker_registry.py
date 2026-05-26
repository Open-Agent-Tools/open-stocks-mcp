"""Unit tests for broker registry management."""

import asyncio

import pytest

from open_stocks_mcp.brokers.registry import (
    BrokerRegistry,
    RegistryNotInitializedError,
    get_broker_registry,
    get_broker_registry_sync,
)
from open_stocks_mcp.monitoring import MetricsCollector
from tests.conftest import MockBroker


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

    @pytest.mark.asyncio
    async def test_run_concurrent_operations_isolates_timeouts(self, registry):
        async def fast() -> dict[str, str]:
            await asyncio.sleep(0.01)
            return {"ok": "fast"}

        async def slow() -> dict[str, str]:
            await asyncio.sleep(0.2)
            return {"ok": "slow"}

        results = await registry.run_concurrent_operations(
            [
                {"broker": "robinhood", "account_id": "acct-1", "operation": fast},
                {"broker": "schwab", "account_id": "acct-2", "operation": slow},
            ],
            concurrency_limit=2,
            timeout_seconds=0.05,
        )
        by_broker = {row["broker"]: row for row in results}
        assert by_broker["robinhood"]["status"] == "success"
        assert "result" in by_broker["robinhood"]
        assert by_broker["schwab"]["status"] == "timeout"
        assert by_broker["schwab"]["error"]["type"] == "timeout"

    @pytest.mark.asyncio
    async def test_coordinated_refresh_is_single_flight_per_account(self, registry):
        calls: dict[str, int] = {"acct-1": 0, "acct-2": 0}

        async def make_refresh(account: str) -> bool:
            calls[account] += 1
            await asyncio.sleep(0.01)
            return True

        async def run_many(account: str) -> list[bool]:
            return await asyncio.gather(
                *[
                    registry.coordinated_refresh(
                        broker_name="robinhood",
                        account_id=account,
                        refresh_coro=lambda a=account: make_refresh(a),
                    )
                    for _ in range(20)
                ]
            )

        acct1, acct2 = await asyncio.gather(run_many("acct-1"), run_many("acct-2"))
        assert all(acct1)
        assert all(acct2)
        assert calls["acct-1"] == 1
        assert calls["acct-2"] == 1

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

    def test_package_reexports_registry_not_initialized_error(self):
        """Test package export includes RegistryNotInitializedError identity."""
        import open_stocks_mcp.brokers as broker_exports

        assert (
            broker_exports.RegistryNotInitializedError
            is RegistryNotInitializedError
        )
        assert "RegistryNotInitializedError" in broker_exports.__all__

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
