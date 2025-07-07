"""Basic tests for open-stocks-mcp package."""

from open_stocks_mcp import __version__


def test_version() -> None:
    """Test that version is defined."""
    assert __version__ == "0.0.2"