"""Alerting primitives and webhook delivery sinks."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlparse

import httpx

from open_stocks_mcp.logging_config import logger

AlertHook = Callable[["AlertEvent"], Awaitable[None]]


@dataclass
class AlertEvent:
    """Normalized alert payload."""

    alert_type: str
    status: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metric_value: float | None = None
    threshold_value: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def signal(self) -> str:
        return str(self.metadata.get("signal", self.alert_type))

    @property
    def severity(self) -> str:
        return self.status

    def as_dict(self) -> dict[str, Any]:
        return {
            "alert_type": self.alert_type,
            "status": self.status,
            "message": self.message,
            "timestamp": self.timestamp,
            "metric_value": self.metric_value,
            "threshold_value": self.threshold_value,
            "metadata": self.metadata,
        }


@runtime_checkable
class AlertSink(Protocol):
    async def send(self, event: AlertEvent) -> None: ...


class WebhookAlertSink:
    """Send alerts to a webhook endpoint via JSON POST."""

    def __init__(self, webhook_url: str, timeout_seconds: float = 3.0):
        parsed = urlparse(webhook_url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Webhook URL must use http or https")
        if parsed.hostname in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Webhook URL cannot target localhost")

        self._webhook_url = webhook_url
        self._timeout_seconds = timeout_seconds

    async def send(self, event: AlertEvent) -> None:
        payload = event.as_dict()
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(self._webhook_url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"Webhook alert failed: {exc}")
        except Exception as exc:
            logger.error(f"Unexpected error sending webhook alert: {exc}")


class LogAlertSink:
    """Default sink that keeps alerts visible in server logs."""

    async def send(self, event: AlertEvent) -> None:
        logger.warning(f"Alert emitted: {event.as_dict()}")


class AlertManager:
    """Dispatch alerts to hooks and sinks with fail-open behavior."""

    def __init__(
        self,
        *,
        enabled: bool,
        hooks: list[AlertHook] | None = None,
        sinks: list[AlertSink] | None = None,
    ):
        self.enabled = enabled
        self._hooks = hooks or []
        self._sinks = sinks or []

    async def emit(self, event: AlertEvent) -> None:
        if not self.enabled:
            return

        for hook in self._hooks:
            try:
                await hook(event)
            except Exception as exc:
                logger.warning(f"Alert hook failed: {exc}")

        for sink in self._sinks:
            try:
                await sink.send(event)
            except Exception as exc:
                logger.warning(f"Alert sink failed: {exc}")
