"""Unit tests for proactive alerting hooks and webhook dispatch."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from open_stocks_mcp.alerting import AlertEvent, AlertManager, WebhookAlertSink


@pytest.mark.asyncio
async def test_alert_manager_disabled_by_default_noop() -> None:
    sink = AsyncMock()
    manager = AlertManager(enabled=False, sinks=[sink])
    await manager.emit(
        AlertEvent(
            alert_type="health_transition",
            status="degraded",
            message="Health degraded",
        )
    )
    sink.send.assert_not_called()


@pytest.mark.asyncio
async def test_alert_manager_emits_to_registered_hook() -> None:
    hook = AsyncMock()
    manager = AlertManager(enabled=True, hooks=[hook])
    event = AlertEvent(
        alert_type="threshold_breach",
        status="degraded",
        message="High error rate",
        metric_value=12.5,
        threshold_value=10.0,
    )
    await manager.emit(event)
    hook.assert_awaited_once()
    emitted = hook.await_args.args[0]
    assert emitted.alert_type == "threshold_breach"
    assert emitted.status == "degraded"


@pytest.mark.asyncio
async def test_webhook_alerter_sends_json_payload() -> None:
    sink = WebhookAlertSink(
        webhook_url="https://example.test/alert", timeout_seconds=1.0
    )
    event = AlertEvent(
        alert_type="threshold_breach",
        status="unhealthy",
        message="Latency threshold exceeded",
        metric_value=155.0,
        threshold_value=100.0,
    )

    with patch("httpx.AsyncClient") as mock_client:
        post = AsyncMock()
        client = AsyncMock()
        client.post = post
        response = Mock()
        post.return_value = response
        mock_client.return_value.__aenter__.return_value = client
        mock_client.return_value.__aexit__.return_value = False

        await sink.send(event)

    post.assert_awaited_once()
    payload = post.await_args.kwargs["json"]
    assert payload["alert_type"] == "threshold_breach"
    assert payload["status"] == "unhealthy"
    assert payload["metric_value"] == 155.0
    assert payload["threshold_value"] == 100.0
    assert "timestamp" in payload
