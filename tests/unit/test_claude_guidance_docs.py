"""Regression checks for the project guidance loaded by Claude Code."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / "CLAUDE.md"
SERVER_APP = ROOT / "src" / "open_stocks_mcp" / "server" / "app.py"
SCHWAB_SETUP = ROOT / "docs" / "SCHWAB_SETUP.md"


def _claude_text() -> str:
    return CLAUDE.read_text(encoding="utf-8")


def _active_mcp_tool_count() -> int:
    app_text = SERVER_APP.read_text(encoding="utf-8")
    return len(re.findall(r"^@mcp\.tool\(\)", app_text, re.MULTILINE))


@pytest.mark.unit
@pytest.mark.journey_system
def test_claude_documents_multi_broker_guidance() -> None:
    text = _claude_text()

    assert "Multi-Broker" in text
    assert "Robinhood" in text
    assert "Charles Schwab" in text

    for env_var in (
        "ROBINHOOD_USERNAME",
        "ROBINHOOD_PASSWORD",
        "SCHWAB_API_KEY",
        "SCHWAB_APP_SECRET",
        "SCHWAB_CALLBACK_URL",
        "SCHWAB_TOKEN_PATH",
    ):
        assert env_var in text

    assert "OAuth" in text
    assert "~/.tokens/schwab_token.json" in text
    assert "schwab_" in text
    assert "live credentials" in text
    assert "Schwab live journey tests" in text
    assert "docs/SCHWAB_INTEGRATION_PLAN.md" in text


@pytest.mark.unit
@pytest.mark.journey_system
def test_claude_links_existing_schwab_setup_guide() -> None:
    text = _claude_text()

    if SCHWAB_SETUP.exists():
        assert "docs/SCHWAB_SETUP.md" in text
        assert "#102" not in text
    else:
        assert "docs/SCHWAB_SETUP.md" not in text
        assert "#102" in text


@pytest.mark.unit
@pytest.mark.journey_system
def test_claude_reflects_active_mcp_tool_count() -> None:
    text = _claude_text()

    assert str(_active_mcp_tool_count()) in text
