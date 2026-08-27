"""Tests for the pluggable broker factory registry."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from open_stocks_mcp.brokers.base import BaseBroker, BrokerAuthStatus
from open_stocks_mcp.brokers.factory import (
    _BROKER_FACTORIES,
    BrokerBuildContext,
    build_broker,
    get_registered_broker_names,
    is_broker_factory_registered,
    register_broker_factory,
)


class _DummyBroker(BaseBroker):
    """Minimal broker for testing."""

    def __init__(self, name: str = "dummy"):
        super().__init__(name)
        self._auth_info.status = BrokerAuthStatus.AUTHENTICATED

    async def authenticate(self) -> bool:
        return True

    async def is_authenticated(self) -> bool:
        return True

    async def logout(self) -> None:
        pass

    async def get_account_info(self) -> dict[str, Any]:
        return {"result": {}}

    async def get_portfolio(self) -> dict[str, Any]:
        return {"result": {}}

    async def get_positions(self) -> dict[str, Any]:
        return {"result": {}}

    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        return {"result": {}}

    async def get_stock_price(self, symbol: str) -> dict[str, Any]:
        return {"result": {}}

    async def order_buy_market(self, symbol: str, quantity: float) -> dict[str, Any]:
        return {"result": {}}

    async def order_sell_market(self, symbol: str, quantity: float) -> dict[str, Any]:
        return {"result": {}}


@pytest.fixture(autouse=True)
def _clean_test_factories():
    """Remove test-only factories registered during each test."""
    before = set(_BROKER_FACTORIES.keys())
    yield
    for key in list(_BROKER_FACTORIES.keys()):
        if key not in before:
            del _BROKER_FACTORIES[key]


@pytest.mark.unit
def test_register_and_lookup():
    called_with: list[BrokerBuildContext] = []

    def factory(ctx: BrokerBuildContext) -> _DummyBroker | None:
        called_with.append(ctx)
        return _DummyBroker("test_broker")

    register_broker_factory("test_broker", factory)

    assert is_broker_factory_registered("test_broker")
    assert "test_broker" in get_registered_broker_names()

    config = MagicMock()
    ctx = BrokerBuildContext(config=config)
    result = build_broker("test_broker", ctx)

    assert isinstance(result, _DummyBroker)
    assert len(called_with) == 1
    assert called_with[0] is ctx


@pytest.mark.unit
def test_build_broker_unknown_returns_none():
    result = build_broker("__no_such_broker__", BrokerBuildContext(config=MagicMock()))
    assert result is None


@pytest.mark.unit
def test_is_broker_factory_registered_false_for_unknown():
    assert not is_broker_factory_registered("__no_such_broker__")


@pytest.mark.unit
def test_factory_returning_none_propagates():
    register_broker_factory("returns_none", lambda ctx: None)
    result = build_broker("returns_none", BrokerBuildContext(config=MagicMock()))
    assert result is None


@pytest.mark.unit
def test_register_normalizes_to_lowercase():
    register_broker_factory("MyBroker", lambda ctx: _DummyBroker())
    assert is_broker_factory_registered("mybroker")
    assert is_broker_factory_registered("MYBROKER")
    assert "mybroker" in get_registered_broker_names()


@pytest.mark.unit
def test_builtin_brokers_are_registered():
    """Importing broker modules triggers their factory registrations."""
    import open_stocks_mcp.brokers.robinhood
    import open_stocks_mcp.brokers.schwab  # noqa: F401

    assert is_broker_factory_registered("robinhood")
    assert is_broker_factory_registered("schwab")


@pytest.mark.unit
def test_third_party_broker_can_register_without_modifying_server_code():
    """Demonstrate the pluggable pattern: register a new broker at import time."""
    factory_called = False

    def alpaca_factory(ctx: BrokerBuildContext) -> _DummyBroker | None:
        nonlocal factory_called
        factory_called = True
        return _DummyBroker("alpaca")

    register_broker_factory("alpaca", alpaca_factory)

    assert is_broker_factory_registered("alpaca")
    broker = build_broker("alpaca", BrokerBuildContext(config=MagicMock()))
    assert isinstance(broker, _DummyBroker)
    assert factory_called


@pytest.mark.unit
def test_broker_build_context_cli_credentials():
    received: list[dict[str, str]] = []

    def factory(ctx: BrokerBuildContext) -> None:
        received.append(dict(ctx.cli_credentials))
        return None

    register_broker_factory("cred_test", factory)

    config = MagicMock()
    ctx = BrokerBuildContext(
        config=config, cli_credentials={"username": "bob", "password": "secret"}
    )
    build_broker("cred_test", ctx)

    assert received == [{"username": "bob", "password": "secret"}]
