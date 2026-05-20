"""Unit tests for monitoring health thresholds."""

from datetime import datetime

import pytest

from open_stocks_mcp.monitoring import MetricsCollector


@pytest.mark.asyncio
async def test_get_health_status_thresholds_map_correctly() -> None:
    collector = MetricsCollector()
    now = datetime.now()

    collector.api_calls.extend(
        [
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
        ]
    )

    collector.errors.extend([(now, "tool", "err")])
    healthy = await collector.get_health_status()
    assert healthy["status"] == "healthy"

    collector.errors.extend([(now, "tool", "err"), (now, "tool", "err")])
    degraded = await collector.get_health_status()
    assert degraded["status"] == "degraded"

    collector.errors.extend([(now, "tool", "err"), (now, "tool", "err"), (now, "tool", "err")])
    unhealthy = await collector.get_health_status()
    assert unhealthy["status"] == "unhealthy"
