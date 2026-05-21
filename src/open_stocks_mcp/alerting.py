"""Alerting primitives for monitoring health and metric threshold events."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx

from open_stocks_mcp.logging_config import logger

AlertHook = Callable[["AlertEvent"], Awaitable[None]]


@dataclass
class AlertConfig:
    """Configuration values controlling alert behavior."""

    enabled: bool = False
    webhook_url: str | None = None
    error_rate_threshold_percent: float = 50.0
    latency_p95_threshold_ms: float = 10000.0
    webhook_timeout_seconds: float = 5.0


@dataclass
class AlertEvent:
    """A normalized alert event payload."""

    alert_type: str
    status: str
    message: str
    timestamp: str
    metric_values: dict[str, float]
    threshold_values: dict[str, float]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-safe payload."""
        return {
            "alert_type": self.alert_type,
            "status": self.status,
            "message": self.message,
            "timestamp": self.timestamp,
            "metric_values": self.metric_values,
            "threshold_values": self.threshold_values,
        }


class AlertManager:
    """Dispatches alert events to registered hooks."""

    def __init__(
        self, config: AlertConfig, hooks: list[AlertHook] | None = None
    ) -> None:
        self.config = config
        self.hooks = hooks or []

    async def dispatch(self, event: AlertEvent) -> None:
        """Fire all hooks for a single event, suppressing hook failures."""
        if not self.config.enabled:
            return
        for hook in self.hooks:
            try:
                await hook(event)
            except Exception:
                logger.exception(
                    "Alert hook failed while dispatching %s", event.alert_type
                )


def create_webhook_alerter(
    webhook_url: str,
    *,
    timeout_seconds: float = 5.0,
) -> AlertHook:
    """Create a hook that POSTs alert events to a webhook endpoint."""

    async def _send_webhook(event: AlertEvent) -> None:
        payload = event.to_payload()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    timeout=timeout_seconds,
                )
                response.raise_for_status()
        except Exception:
            logger.exception("Webhook alert dispatch failed to %s", webhook_url)

    return _send_webhook
