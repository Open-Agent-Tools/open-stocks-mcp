"""Component-level health status aggregation for the MCP server."""

import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from open_stocks_mcp.brokers.base import BrokerAuthStatus
from open_stocks_mcp.brokers.registry import BrokerRegistry, get_broker_registry
from open_stocks_mcp.brokers.session_state import SessionManager, get_session_manager
from open_stocks_mcp.config import load_config
from open_stocks_mcp.monitoring import MetricsCollector, get_metrics_collector


class ComponentStatus(Enum):
    """Discrete component health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Component health payload."""

    name: str
    status: ComponentStatus
    last_checked: datetime
    detail: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize component health."""
        payload: dict[str, Any] = {
            "status": self.status.value,
            "last_checked": self.last_checked.isoformat(),
        }
        if self.detail is not None:
            payload["detail"] = self.detail
        if self.error_message is not None:
            payload["error_message"] = self.error_message
        return payload


class HealthService:
    """Aggregates server health from cached component state."""

    def __init__(
        self,
        registry: BrokerRegistry | None = None,
        metrics_collector: MetricsCollector | None = None,
        session_manager: SessionManager | None = None,
        monitoring_enabled: bool = True,
    ) -> None:
        self.registry = registry
        self.metrics_collector = metrics_collector
        self.session_manager = session_manager
        self.monitoring_enabled = monitoring_enabled

    @staticmethod
    def _map_broker_auth_status(status: BrokerAuthStatus) -> ComponentStatus:
        if status == BrokerAuthStatus.AUTHENTICATED:
            return ComponentStatus.HEALTHY
        if status in (BrokerAuthStatus.AUTHENTICATING, BrokerAuthStatus.MFA_REQUIRED):
            return ComponentStatus.DEGRADED
        return ComponentStatus.UNHEALTHY

    @staticmethod
    def _component_from_status_value(status: str) -> ComponentStatus:
        if status == ComponentStatus.UNHEALTHY.value:
            return ComponentStatus.UNHEALTHY
        if status == ComponentStatus.DEGRADED.value:
            return ComponentStatus.DEGRADED
        return ComponentStatus.HEALTHY

    async def _get_registry(self) -> BrokerRegistry | None:
        if self.registry is None:
            try:
                self.registry = await get_broker_registry()
            except Exception:
                return None
        return self.registry

    def _get_session_manager(self) -> SessionManager:
        if self.session_manager is not None:
            return self.session_manager
        return get_session_manager()

    def _get_metrics_collector(self) -> MetricsCollector:
        if self.metrics_collector is None:
            self.metrics_collector = get_metrics_collector()
        return self.metrics_collector

    async def get_status(self) -> dict[str, Any]:
        """Return aggregated health status and component details."""
        now = datetime.now()
        components: dict[str, dict[str, Any]] = {}
        component_states: list[ComponentStatus] = []

        if self.monitoring_enabled:
            metrics = await self._get_metrics_collector().get_health_status()
            metrics_state = self._component_from_status_value(
                str(metrics.get("status", "healthy"))
            )
            metrics_component = ComponentHealth(
                name="metrics",
                status=metrics_state,
                last_checked=now,
                detail=(
                    ", ".join(metrics.get("issues", []))
                    if metrics.get("issues")
                    else None
                ),
            )
        else:
            metrics_component = ComponentHealth(
                name="metrics",
                status=ComponentStatus.HEALTHY,
                last_checked=now,
                detail="monitoring disabled",
            )
        components["metrics"] = metrics_component.to_dict()
        component_states.append(metrics_component.status)

        session_info = self._get_session_manager().get_session_info()
        session_status = (
            ComponentStatus.HEALTHY
            if session_info.get("authenticated", False)
            else ComponentStatus.UNHEALTHY
        )
        session_component = ComponentHealth(
            name="session",
            status=session_status,
            last_checked=now,
            detail=(
                f"session_duration={session_info.get('session_duration')}"
                if session_info.get("session_duration") is not None
                else None
            ),
        )
        components["session"] = session_component.to_dict()
        component_states.append(session_component.status)

        broker_states: list[ComponentStatus] = []
        registry = await self._get_registry()
        if registry is not None:
            for broker_name in registry.list_brokers():
                broker = registry.get_broker(broker_name)
                if broker is None:
                    continue
                broker_status = self._map_broker_auth_status(broker.auth_info.status)
                broker_component = ComponentHealth(
                    name=f"broker:{broker_name}",
                    status=broker_status,
                    last_checked=now,
                    error_message=broker.auth_info.error_message,
                )
                components[f"broker:{broker_name}"] = broker_component.to_dict()
                component_states.append(broker_component.status)
                broker_states.append(broker_component.status)

        # Overall status aggregation. Unhealthy if any core component (metrics/session)
        # is unhealthy, or if all configured brokers are unhealthy.
        overall = ComponentStatus.HEALTHY
        core_states = [metrics_component.status, session_component.status]

        if any(state == ComponentStatus.UNHEALTHY for state in core_states) or (
            broker_states
            and all(state == ComponentStatus.UNHEALTHY for state in broker_states)
        ):
            overall = ComponentStatus.UNHEALTHY
        elif any(
            state == ComponentStatus.DEGRADED for state in component_states
        ) or any(state == ComponentStatus.UNHEALTHY for state in broker_states):
            overall = ComponentStatus.DEGRADED

        return {
            "status": overall.value,
            "components": components,
            "timestamp": time.time(),
        }


_health_service: HealthService | None = None


def get_health_service() -> HealthService:
    """Get process-wide health service singleton."""
    global _health_service
    if _health_service is None:
        config = load_config()
        _health_service = HealthService(monitoring_enabled=config.monitoring_enabled)
    return _health_service
