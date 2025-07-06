"""Basic tests for open-stocks-mcp package."""

import pytest

from open_stocks_mcp import __version__
from open_stocks_mcp.tools.echo import echo


def test_version() -> None:
    """Test that version is defined."""
    assert __version__ == "0.1.0"


def test_echo_basic() -> None:
    """Test basic echo functionality."""
    result = echo("hello")
    assert result.type == "text"
    assert result.text == "hello"


def test_echo_upper_transform() -> None:
    """Test echo with upper case transformation."""
    result = echo("hello", transform="upper")
    assert result.text == "HELLO"


def test_echo_lower_transform() -> None:
    """Test echo with lower case transformation."""
    result = echo("HELLO", transform="lower")
    assert result.text == "hello"


def test_echo_invalid_transform() -> None:
    """Test echo with invalid transformation."""
    result = echo("hello", transform="invalid")
    assert result.text == "hello"


@pytest.mark.slow
def test_echo_performance() -> None:
    """Test echo performance (marked as slow)."""
    # Simple performance test
    import time

    start = time.time()
    for _ in range(1000):
        echo("test")
    duration = time.time() - start

    # Should complete very quickly
    assert duration < 1.0
