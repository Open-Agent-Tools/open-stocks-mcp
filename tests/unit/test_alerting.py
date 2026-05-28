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
    event = AlertEvent(
        alert_type="threshold_breach",
        status="unhealthy",
        message="Latency threshold exceeded",
        metric_value=155.0,
        threshold_value=100.0,
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_instance = AsyncMock()
        mock_client_class.return_value = mock_instance
        response = Mock()
        response.raise_for_status = Mock()
        mock_instance.post = AsyncMock(return_value=response)

        sink = WebhookAlertSink(
            webhook_url="https://example.test/alert", timeout_seconds=1.0
        )
        await sink.send(event)

    mock_instance.post.assert_awaited_once()
    payload = mock_instance.post.await_args.kwargs["json"]
    assert payload["alert_type"] == "threshold_breach"
    assert payload["status"] == "unhealthy"
    assert payload["metric_value"] == 155.0
    assert payload["threshold_value"] == 100.0
    assert "timestamp" in payload


@pytest.mark.asyncio
async def test_webhook_alerter_reuses_client_across_sends() -> None:
    event = AlertEvent(alert_type="test", status="ok", message="ping")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_instance = AsyncMock()
        mock_client_class.return_value = mock_instance
        mock_instance.post = AsyncMock(return_value=Mock(raise_for_status=Mock()))

        sink = WebhookAlertSink("https://example.test/alert")
        await sink.send(event)
        await sink.send(event)

    # Constructor called once; post called twice with the same client
    mock_client_class.assert_called_once()
    assert mock_instance.post.await_count == 2


@pytest.mark.asyncio
async def test_webhook_alerter_aclose_closes_client() -> None:
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_instance = AsyncMock()
        mock_client_class.return_value = mock_instance

        sink = WebhookAlertSink("https://example.test/alert")
        await sink.aclose()

    mock_instance.aclose.assert_awaited_once()


def test_webhook_sink_url_validation() -> None:
    # Valid
    WebhookAlertSink("https://example.com/alert")

    # Invalid scheme
    with pytest.raises(ValueError, match="Webhook URL must use http or https"):
        WebhookAlertSink("ftp://example.com/alert")

    # localhost
    with pytest.raises(ValueError, match="Webhook URL cannot target localhost"):
        WebhookAlertSink("https://localhost/alert")
    with pytest.raises(ValueError, match="Webhook URL cannot target localhost"):
        WebhookAlertSink("http://127.0.0.1/alert")
    with pytest.raises(ValueError, match="Webhook URL cannot target localhost"):
        WebhookAlertSink("https://[::1]/alert")
