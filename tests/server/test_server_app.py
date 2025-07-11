"""Tests for server app module."""

from unittest.mock import MagicMock, patch

import pytest

from open_stocks_mcp.server.app import attempt_login, create_mcp_server, mcp


class TestServerApp:
    """Test server app functionality."""

    def test_mcp_server_instance_exists(self) -> None:
        """Test that global mcp server instance exists."""
        assert mcp is not None
        assert hasattr(mcp, "tool")

    def test_create_mcp_server_returns_mcp_instance(self) -> None:
        """Test create_mcp_server returns the global mcp instance."""
        with (
            patch("open_stocks_mcp.server.app.load_config") as mock_config,
            patch("open_stocks_mcp.server.app.setup_logging") as mock_logging,
        ):
            mock_config.return_value = MagicMock()
            result = create_mcp_server()

            assert result is mcp
            mock_config.assert_called_once()
            mock_logging.assert_called_once()

    def test_create_mcp_server_with_config(self) -> None:
        """Test create_mcp_server with provided config."""
        mock_config = MagicMock()

        with patch("open_stocks_mcp.server.app.setup_logging") as mock_logging:
            result = create_mcp_server(mock_config)

            assert result is mcp
            mock_logging.assert_called_once_with(mock_config)


class TestAttemptLogin:
    """Test attempt_login functionality."""

    def test_attempt_login_success(self) -> None:
        """Test successful login attempt."""
        mock_session_manager = MagicMock()
        mock_session_manager.ensure_authenticated.return_value = True
        mock_session_manager.get_session_info.return_value = {
            "username": "testuser",
            "authenticated": True,
        }

        with (
            patch(
                "open_stocks_mcp.server.app.get_session_manager",
                return_value=mock_session_manager,
            ),
            patch(
                "open_stocks_mcp.server.app.asyncio.run", return_value=True
            ) as mock_run,
            patch("open_stocks_mcp.server.app.logger") as mock_logger,
        ):
            # Should not raise any exception
            attempt_login("testuser", "testpass")

            mock_session_manager.set_credentials.assert_called_once_with(
                "testuser", "testpass"
            )
            mock_run.assert_called_once()
            mock_session_manager.get_session_info.assert_called_once()
            mock_logger.info.assert_called()

    def test_attempt_login_no_user_profile(self) -> None:
        """Test login attempt when authentication fails."""
        mock_session_manager = MagicMock()
        mock_session_manager.ensure_authenticated.return_value = False

        with (
            patch(
                "open_stocks_mcp.server.app.get_session_manager",
                return_value=mock_session_manager,
            ),
            patch(
                "open_stocks_mcp.server.app.asyncio.run", return_value=False
            ) as mock_run,
            patch("open_stocks_mcp.server.app.logger") as mock_logger,
            patch("open_stocks_mcp.server.app.sys.exit") as mock_exit,
        ):
            attempt_login("testuser", "testpass")

            mock_session_manager.set_credentials.assert_called_once_with(
                "testuser", "testpass"
            )
            mock_run.assert_called_once()
            mock_logger.error.assert_called()
            mock_exit.assert_called_once_with(1)

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    def test_attempt_login_exception(self) -> None:
        """Test login attempt when an exception occurs."""
        mock_session_manager = MagicMock()
        mock_session_manager.set_credentials.side_effect = Exception("Login failed")

        with (
            patch(
                "open_stocks_mcp.server.app.get_session_manager",
                return_value=mock_session_manager,
            ),
            patch("open_stocks_mcp.server.app.logger") as mock_logger,
            patch("open_stocks_mcp.server.app.sys.exit") as mock_exit,
        ):
            attempt_login("testuser", "testpass")

            mock_session_manager.set_credentials.assert_called_once_with(
                "testuser", "testpass"
            )
            mock_logger.error.assert_called()
            mock_exit.assert_called_once_with(1)


class TestToolRegistration:
    """Test that all tools are properly registered."""

    @pytest.mark.asyncio
    async def test_tools_are_registered(self) -> None:
        """Test that all expected tools are registered on the mcp server."""
        # Get the list of registered tools via list_tools method
        tools_list = await mcp.list_tools()
        tool_names = [tool.name for tool in tools_list]

        expected_tools = [
            "account_info",
            "account_details",
            "positions",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"

    @pytest.mark.asyncio
    async def test_account_info_tool_callable(self) -> None:
        """Test that account_info tool is callable."""
        tools_list = await mcp.list_tools()
        account_info_tool = None

        for tool in tools_list:
            if tool.name == "account_info":
                account_info_tool = tool
                break

        assert account_info_tool is not None
        assert (
            account_info_tool.description == "Gets basic Robinhood account information."
        )
