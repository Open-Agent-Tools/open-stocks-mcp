"""Unit tests for component health aggregation."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from open_stocks_mcp.brokers.base import BrokerAuthStatus
from open_stocks_mcp.config import load_config
from open_stocks_mcp.health import HealthService, get_health_service


def _fake_broker(
    name: str, status: BrokerAuthStatus, error_message: str | None = None
) -> MagicMock:
    broker = MagicMock()
    broker.name = name
    broker.auth_info.status = status
    broker.auth_info.error_message = error_message
    return broker


@pytest.mark.asyncio
async def test_get_status_returns_structured_snapshot_from_cached_broker_status() -> (
    None
):
    registry = MagicMock()
    robinhood = _fake_broker("robinhood", BrokerAuthStatus.AUTHENTICATED)
    schwab = _fake_broker("schwab", BrokerAuthStatus.NOT_CONFIGURED)
    registry.list_brokers.return_value = ["robinhood", "schwab"]
    registry.get_broker.side_effect = lambda name: {
        "robinhood": robinhood,
        "schwab": schwab,
    }[name]

    metrics_collector = AsyncMock()
    metrics_collector.get_health_status.return_value = {
        "status": "healthy",
        "issues": [],
    }

    session_manager = MagicMock()
    session_manager.get_session_info.return_value = {
        "is_authenticated": True,
        "session_duration": 123,
    }

    service = HealthService(
        registry=registry,
        metrics_collector=metrics_collector,
        session_manager=session_manager,
    )

    result = await service.get_status()

    assert set(result.keys()) == {"status", "components", "timestamp"}
    assert result["components"]["broker:robinhood"]["status"] == "healthy"
    assert result["components"]["broker:schwab"]["status"] == "unhealthy"
    assert result["components"]["metrics"]["status"] == "healthy"
    assert result["status"] == "degraded"
    assert not robinhood.authenticate.called
    assert not robinhood.is_authenticated.called
    assert not robinhood.get_account_info.called
    assert not schwab.authenticate.called
    assert not schwab.is_authenticated.called
    assert not schwab.get_account_info.called


@pytest.mark.asyncio
async def test_metrics_component_transitions_healthy_to_degraded_to_unhealthy() -> None:
    registry = MagicMock()
    registry.list_brokers.return_value = []
    metrics_collector = AsyncMock()
    metrics_collector.get_health_status.side_effect = [
        {"status": "healthy", "issues": []},
        {"status": "degraded", "issues": ["a"]},
        {"status": "unhealthy", "issues": ["b"]},
    ]
    session_manager = MagicMock()
    session_manager.get_session_info.return_value = {"is_authenticated": True}

    service = HealthService(
        registry=registry,
        metrics_collector=metrics_collector,
        session_manager=session_manager,
    )

    first = await service.get_status()
    second = await service.get_status()
    third = await service.get_status()

    assert first["components"]["metrics"]["status"] == "healthy"
    assert second["components"]["metrics"]["status"] == "degraded"
    assert third["components"]["metrics"]["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_broker_component_transitions_on_auth_status_change() -> None:
    broker = _fake_broker("robinhood", BrokerAuthStatus.NOT_CONFIGURED)
    registry = MagicMock()
    registry.list_brokers.return_value = ["robinhood"]
    registry.get_broker.return_value = broker
    metrics_collector = AsyncMock()
    metrics_collector.get_health_status.return_value = {
        "status": "healthy",
        "issues": [],
    }
    session_manager = MagicMock()
    session_manager.get_session_info.return_value = {"is_authenticated": True}
    service = HealthService(
        registry=registry,
        metrics_collector=metrics_collector,
        session_manager=session_manager,
    )

    s1 = await service.get_status()
    broker.auth_info.status = BrokerAuthStatus.AUTHENTICATING
    s2 = await service.get_status()
    broker.auth_info.status = BrokerAuthStatus.AUTHENTICATED
    s3 = await service.get_status()
    broker.auth_info.status = BrokerAuthStatus.TOKEN_EXPIRED
    s4 = await service.get_status()

    assert s1["components"]["broker:robinhood"]["status"] == "unhealthy"
    assert s2["components"]["broker:robinhood"]["status"] == "degraded"
    assert s3["components"]["broker:robinhood"]["status"] == "healthy"
    assert s4["components"]["broker:robinhood"]["status"] == "unhealthy"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("broker_status", "expected"),
    [
        (BrokerAuthStatus.AUTHENTICATED, "healthy"),
        (BrokerAuthStatus.AUTHENTICATING, "degraded"),
        (BrokerAuthStatus.MFA_REQUIRED, "degraded"),
        (BrokerAuthStatus.NOT_CONFIGURED, "unhealthy"),
        (BrokerAuthStatus.NOT_AUTHENTICATED, "unhealthy"),
        (BrokerAuthStatus.AUTH_FAILED, "unhealthy"),
        (BrokerAuthStatus.TOKEN_EXPIRED, "unhealthy"),
    ],
)
async def test_broker_auth_status_mapping(
    broker_status: BrokerAuthStatus, expected: str
) -> None:
    broker = _fake_broker("robinhood", broker_status)
    registry = MagicMock()
    registry.list_brokers.return_value = ["robinhood"]
    registry.get_broker.return_value = broker
    metrics_collector = AsyncMock()
    metrics_collector.get_health_status.return_value = {
        "status": "healthy",
        "issues": [],
    }
    session_manager = MagicMock()
    session_manager.get_session_info.return_value = {"is_authenticated": True}
    service = HealthService(
        registry=registry,
        metrics_collector=metrics_collector,
        session_manager=session_manager,
    )

    status = await service.get_status()
    assert status["components"]["broker:robinhood"]["status"] == expected


@pytest.mark.asyncio
async def test_overall_status_aggregation_rules() -> None:
    metrics_collector = AsyncMock()
    metrics_collector.get_health_status.return_value = {
        "status": "healthy",
        "issues": [],
    }

    registry_partial = MagicMock()
    broker_ok = _fake_broker("robinhood", BrokerAuthStatus.AUTHENTICATED)
    broker_bad = _fake_broker("schwab", BrokerAuthStatus.NOT_CONFIGURED)
    registry_partial.list_brokers.return_value = ["robinhood", "schwab"]
    registry_partial.get_broker.side_effect = lambda name: {
        "robinhood": broker_ok,
        "schwab": broker_bad,
    }[name]

    session_healthy = MagicMock()
    session_healthy.get_session_info.return_value = {"is_authenticated": True}
    partial = HealthService(
        registry=registry_partial,
        metrics_collector=metrics_collector,
        session_manager=session_healthy,
    )
    assert (await partial.get_status())["status"] == "degraded"

    registry_all_bad = MagicMock()
    registry_all_bad.list_brokers.return_value = ["robinhood"]
    registry_all_bad.get_broker.return_value = _fake_broker(
        "robinhood", BrokerAuthStatus.NOT_AUTHENTICATED
    )
    all_bad = HealthService(
        registry=registry_all_bad,
        metrics_collector=metrics_collector,
        session_manager=session_healthy,
    )
    assert (await all_bad.get_status())["status"] == "unhealthy"

    session_unhealthy = MagicMock()
    session_unhealthy.get_session_info.return_value = {"is_authenticated": False}
    core_unhealthy = HealthService(
        registry=registry_partial,
        metrics_collector=metrics_collector,
        session_manager=session_unhealthy,
    )
    assert (await core_unhealthy.get_status())["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_registry_lookup_failure_omits_broker_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_registry() -> None:
        raise RuntimeError("registry init failed")

    monkeypatch.setattr("open_stocks_mcp.health.get_broker_registry", fail_registry)
    metrics_collector = AsyncMock()
    metrics_collector.get_health_status.return_value = {
        "status": "healthy",
        "issues": [],
    }
    session_manager = MagicMock()
    session_manager.get_session_info.return_value = {"is_authenticated": True}
    service = HealthService(
        registry=None,
        metrics_collector=metrics_collector,
        session_manager=session_manager,
    )

    result = await service.get_status()
    assert result["status"] == "healthy"
    assert "broker:robinhood" not in result["components"]


@pytest.mark.asyncio
async def test_monitoring_disabled_skips_metrics_collection() -> None:
    registry = MagicMock()
    registry.list_brokers.return_value = []
    metrics_collector = AsyncMock()
    session_manager = MagicMock()
    session_manager.get_session_info.return_value = {"is_authenticated": True}
    service = HealthService(
        registry=registry,
        metrics_collector=metrics_collector,
        session_manager=session_manager,
        monitoring_enabled=False,
    )

    result = await service.get_status()
    metrics_collector.get_health_status.assert_not_called()
    assert result["components"]["metrics"]["status"] == "healthy"
    assert result["components"]["metrics"]["detail"] == "monitoring disabled"


def test_load_config_reads_monitoring_enabled_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MONITORING_ENABLED", "false")
    cfg = load_config()
    assert cfg.monitoring_enabled is False

    monkeypatch.delenv("MONITORING_ENABLED", raising=False)
    cfg_default = load_config()
    assert cfg_default.monitoring_enabled is True


def test_get_health_service_returns_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("open_stocks_mcp.health._health_service", None)
    first = get_health_service()
    second = get_health_service()
    assert first is second
