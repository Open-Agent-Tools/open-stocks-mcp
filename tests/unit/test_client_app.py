"""Unit tests for the MCP client CLI and app."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner
from mcp.types import CallToolResult, TextContent

from open_stocks_mcp.client import main as package_main
from open_stocks_mcp.client.app import call_tool, main

pytestmark = [pytest.mark.unit, pytest.mark.journey_system]


@pytest.mark.asyncio
async def test_call_tool_initializes_stdio_session_and_returns_text():
    """Test that call_tool initializes a session and returns text content."""
    tool_name = "test_tool"
    arguments = {"arg1": "val1"}
    expected_text = "tool response"

    # Mock TextContent
    mock_content = TextContent(type="text", text=expected_text)
    mock_result = MagicMock(spec=CallToolResult)
    mock_result.content = [mock_content]

    # Mock Session
    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.call_tool = AsyncMock(return_value=mock_result)

    # Mock stdio_client context manager
    mock_stdio_cm = MagicMock()
    mock_stdio_cm.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
    mock_stdio_cm.__aexit__ = AsyncMock()

    # Mock ClientSession context manager
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cm.__aexit__ = AsyncMock()

    with (
        patch("open_stocks_mcp.client.app.stdio_client", return_value=mock_stdio_cm) as mock_stdio,
        patch("open_stocks_mcp.client.app.ClientSession", return_value=mock_session_cm),
    ):
        result = await call_tool(tool_name, arguments)

        assert result == expected_text
        mock_stdio.assert_called_once()
        args, _ = mock_stdio.call_args
        server_params = args[0]
        assert server_params.command == "open-stocks-mcp-server"
        assert server_params.args == []
        assert server_params.env is None

        mock_session.initialize.assert_awaited_once()
        mock_session.call_tool.assert_awaited_once_with(tool_name, arguments=arguments)


@pytest.mark.asyncio
async def test_call_tool_uses_empty_arguments_when_none():
    """Test that call_tool uses an empty dict when arguments are None."""
    tool_name = "health_check"

    mock_content = TextContent(type="text", text="ok")
    mock_result = MagicMock(spec=CallToolResult)
    mock_result.content = [mock_content]

    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.call_tool = AsyncMock(return_value=mock_result)

    mock_stdio_cm = MagicMock()
    mock_stdio_cm.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
    mock_stdio_cm.__aexit__ = AsyncMock()

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cm.__aexit__ = AsyncMock()

    with (
        patch("open_stocks_mcp.client.app.stdio_client", return_value=mock_stdio_cm),
        patch("open_stocks_mcp.client.app.ClientSession", return_value=mock_session_cm),
    ):
        await call_tool(tool_name)
        mock_session.call_tool.assert_awaited_once_with(tool_name, arguments={})


@pytest.mark.asyncio
async def test_call_tool_falls_back_to_result_string_when_no_text_content():
    """Test that call_tool falls back to str(result) when no text content is found."""
    tool_name = "test_tool"
    sentinel_str = "sentinel_result"

    mock_result = MagicMock(spec=CallToolResult)
    mock_result.content = []
    mock_result.__str__.return_value = sentinel_str

    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.call_tool = AsyncMock(return_value=mock_result)

    mock_stdio_cm = MagicMock()
    mock_stdio_cm.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
    mock_stdio_cm.__aexit__ = AsyncMock()

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cm.__aexit__ = AsyncMock()

    with (
        patch("open_stocks_mcp.client.app.stdio_client", return_value=mock_stdio_cm),
        patch("open_stocks_mcp.client.app.ClientSession", return_value=mock_session_cm),
    ):
        result = await call_tool(tool_name)
        assert result == sentinel_str


def test_main_parses_message_and_prints_response():
    """Test the Click entry point parses arguments and prints the response."""
    runner = CliRunner()
    expected_response = "mocked response"

    with patch("open_stocks_mcp.client.app.call_tool", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = expected_response

        result = runner.invoke(main, ["get_stock_orders status=pending symbol=AAPL"])

        assert result.exit_code == 0
        assert expected_response in result.output
        mock_call.assert_awaited_once_with(
            "get_stock_orders", {"status": "pending", "symbol": "AAPL"}
        )


def test_main_splits_argument_values_once_and_ignores_non_key_tokens():
    """Test argument parsing edge cases in main."""
    runner = CliRunner()

    with patch("open_stocks_mcp.client.app.call_tool", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "ok"

        # query=foo=bar should result in key='query', value='foo=bar'
        # ignored-token should be ignored
        runner.invoke(main, ["search query=foo=bar ignored-token"])

        mock_call.assert_awaited_once_with("search", {"query": "foo=bar"})


def test_client_package_exports_main_command():
    """Test that the package export resolves to the correct Click command."""
    assert package_main is main
