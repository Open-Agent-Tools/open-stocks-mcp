"""Regression tests: Docker compose token volumes must not use host bind mounts."""

from pathlib import Path

import pytest
import yaml

DOCKER_DIR = Path(__file__).resolve().parents[2] / "examples" / "open-stocks-mcp-docker"

COMPOSE_FILES = [
    DOCKER_DIR / "docker-compose.yml",
    DOCKER_DIR / "docker-compose.dev.yml",
]


@pytest.fixture(params=COMPOSE_FILES, ids=lambda p: p.name)
def compose_config(request: pytest.FixtureRequest) -> dict:
    return yaml.safe_load(request.param.read_text())


def test_mcp_tokens_volume_is_not_bind_backed(compose_config: dict) -> None:
    vol = compose_config.get("volumes", {}).get("mcp_tokens", {})
    if vol is None:
        return
    driver_opts = vol.get("driver_opts", {})
    assert "device" not in driver_opts, "mcp_tokens must not bind-mount a host path"
    assert driver_opts.get("o") != "bind", "mcp_tokens must not use 'o: bind'"
    assert driver_opts.get("type") != "none", "mcp_tokens must not use 'type: none'"


def test_service_mounts_mcp_tokens(compose_config: dict) -> None:
    for svc_name, svc in compose_config.get("services", {}).items():
        vols = svc.get("volumes", [])
        token_mounts = [
            v
            for v in vols
            if isinstance(v, str) and v.startswith("mcp_tokens:")
        ]
        assert token_mounts, f"service '{svc_name}' must mount mcp_tokens"
        assert any(
            v == "mcp_tokens:/home/mcp/.tokens" for v in token_mounts
        ), f"service '{svc_name}' must mount mcp_tokens at /home/mcp/.tokens"
