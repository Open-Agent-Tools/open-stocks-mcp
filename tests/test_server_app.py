"""Tests for server app module."""

from unittest.mock import MagicMock, patch

import pytest

from open_stocks_mcp.server.app import attempt_login, create_mcp_server, mcp


class TestServerApp:
    """Test server app functionality."""

    def test_mcp_server_instance_exists(self):
        """Test that global mcp server instance exists."""
        assert mcp is not None
        assert hasattr(mcp, "tool")

    def test_create_mcp_server_returns_mcp_instance(self):
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

    def test_create_mcp_server_with_config(self):
        """Test create_mcp_server with provided config."""
        mock_config = MagicMock()

        with patch("open_stocks_mcp.server.app.setup_logging") as mock_logging:
            result = create_mcp_server(mock_config)

            assert result is mcp
            mock_logging.assert_called_once_with(mock_config)


class TestAttemptLogin:
    """Test attempt_login functionality."""

    def test_attempt_login_success(self):
        """Test successful login attempt."""
        mock_user_profile = {"username": "testuser", "id": "123"}

        with (
            patch("open_stocks_mcp.server.app.rh.login") as mock_login,
            patch(
                "open_stocks_mcp.server.app.rh.load_user_profile",
                return_value=mock_user_profile,
            ) as mock_profile,
            patch("open_stocks_mcp.server.app.logger") as mock_logger,
        ):
            # Should not raise any exception
            attempt_login("testuser", "testpass")

            mock_login.assert_called_once_with(
                username="testuser", password="testpass", store_session=True
            )
            mock_profile.assert_called_once()
            mock_logger.info.assert_called()

    def test_attempt_login_no_user_profile(self):
        """Test login attempt when user profile retrieval fails."""
        with (
            patch("open_stocks_mcp.server.app.rh.login") as mock_login,
            patch(
                "open_stocks_mcp.server.app.rh.load_user_profile", return_value=None
            ) as mock_profile,
            patch("open_stocks_mcp.server.app.logger") as mock_logger,
            patch("open_stocks_mcp.server.app.sys.exit") as mock_exit,
        ):
            attempt_login("testuser", "testpass")

            mock_login.assert_called_once()
            mock_profile.assert_called_once()
            mock_logger.error.assert_called()
            mock_exit.assert_called_once_with(1)

    def test_attempt_login_exception(self):
        """Test login attempt with exception."""
        with (
            patch(
                "open_stocks_mcp.server.app.rh.login",
                side_effect=Exception("Login failed"),
            ) as mock_login,
            patch("open_stocks_mcp.server.app.logger") as mock_logger,
            patch("open_stocks_mcp.server.app.sys.exit") as mock_exit,
        ):
            attempt_login("testuser", "testpass")

            mock_login.assert_called_once()
            mock_logger.error.assert_called()
            mock_exit.assert_called_once_with(1)


class TestToolRegistration:
    """Test that all tools are properly registered."""

    @pytest.mark.asyncio
    async def test_tools_are_registered(self):
        """Test that all expected tools are registered on the mcp server."""
        # Get the list of registered tools via list_tools method
        tools_list = await mcp.list_tools()
        tool_names = [tool.name for tool in tools_list]

        expected_tools = [
            "account_info",
            "portfolio",
            "stock_orders",
            "options_orders",
            "account_details",
            "positions",
            "portfolio_history",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"

    @pytest.mark.asyncio
    async def test_account_info_tool_callable(self):
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

    @pytest.mark.asyncio
    async def test_portfolio_history_tool_has_parameters(self):
        """Test that portfolio_history tool has span parameter."""
        tools_list = await mcp.list_tools()
        portfolio_history_tool = None

        for tool in tools_list:
            if tool.name == "portfolio_history":
                portfolio_history_tool = tool
                break

        assert portfolio_history_tool is not None
        # Check that the tool has parameters defined
        assert portfolio_history_tool.inputSchema is not None
