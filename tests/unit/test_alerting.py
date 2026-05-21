"""Unit tests for alerting hooks and webhook dispatch."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock

import pytest

from open_stocks_mcp.alerting import (
    AlertConfig,
    AlertEvent,
    AlertManager,
    create_webhook_alerter,
)
from open_stocks_mcp.monitoring import MetricsCollector


@pytest.mark.asyncio
async def test_alert_manager_disabled_by_default_noop() -> None:
    events: list[AlertEvent] = []

    async def hook(event: AlertEvent) -> None:
        events.append(event)

    manager = AlertManager(config=AlertConfig(), hooks=[hook])
    event = AlertEvent(
        alert_type="health_transition",
        status="degraded",
        message="Health transitioned to degraded",
        timestamp=datetime.now().isoformat(),
        metric_values={"error_rate_percent": 12.0},
        threshold_values={},
    )

    await manager.dispatch(event)
    assert events == []


@pytest.mark.asyncio
async def test_webhook_alerter_posts_json_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post_mock = Mock()

    class _Response:
        def raise_for_status(self) -> None:
            return None

    class _Client:
        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict, timeout: float) -> _Response:
            post_mock(url, json, timeout)
            return _Response()

    monkeypatch.setattr("httpx.AsyncClient", _Client)

    event = AlertEvent(
        alert_type="threshold_breach",
        status="warning",
        message="Error rate threshold breached",
        timestamp=datetime.now().isoformat(),
        metric_values={"error_rate_percent": 55.0, "p95_response_time_ms": 1200.0},
        threshold_values={"error_rate_threshold_percent": 50.0},
    )

    webhook = create_webhook_alerter("https://alerts.example.test/hook")
    await webhook(event)

    assert post_mock.call_count == 1


@pytest.mark.asyncio
async def test_health_transition_alert_emitted_once_per_state_change() -> None:
    events: list[AlertEvent] = []

    async def hook(event: AlertEvent) -> None:
        events.append(event)

    collector = MetricsCollector(
        alert_config=AlertConfig(enabled=True),
        alert_hooks=[hook],
    )
    now = datetime.now()
    collector.api_calls.extend([(now, "tool", True) for _ in range(10)])

    collector.errors.extend([(now, "tool", "err"), (now, "tool", "err")])
    first = await collector.get_health_status()
    second = await collector.get_health_status()

    assert first["status"] == "degraded"
    assert second["status"] == "degraded"
    health_events = [e for e in events if e.alert_type == "health_transition"]
    assert len(health_events) == 1


@pytest.mark.asyncio
async def test_threshold_alerts_fire_only_on_breach() -> None:
    events: list[AlertEvent] = []

    async def hook(event: AlertEvent) -> None:
        events.append(event)

    collector = MetricsCollector(
        alert_config=AlertConfig(
            enabled=True,
            error_rate_threshold_percent=20.0,
            latency_p95_threshold_ms=1000.0,
        ),
        alert_hooks=[hook],
    )
    now = datetime.now()

    collector.api_calls.extend([(now, "tool", True) for _ in range(20)])
    collector.response_times.extend([(now, 0.25) for _ in range(20)])
    await collector.get_health_status()

    threshold_events = [e for e in events if e.alert_type == "threshold_breach"]
    assert threshold_events == []

    collector.errors.extend([(now, "tool", "err") for _ in range(8)])
    collector.response_times.clear()
    collector.response_times.extend([(now, 2.0) for _ in range(20)])

    await collector.get_health_status()
    await collector.get_health_status()

    threshold_events = [e for e in events if e.alert_type == "threshold_breach"]
    assert len(threshold_events) == 2
