"""Tests for server app module."""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from open_stocks_mcp.config import (
    BrokerSettings,
    RobinhoodConfig,
    SchwabConfig,
    ServerConfig,
)
from open_stocks_mcp.server.app import (
    attempt_login,
    create_mcp_server,
    health_check,
    main,
    mcp,
    setup_brokers,
)


@pytest.mark.journey_system
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
            patch("open_stocks_mcp.server.app.configure_global_rate_limiter"),
        ):
            mock_cfg = MagicMock()
            mock_cfg.otel.enabled = False
            mock_config.return_value = mock_cfg
            result = create_mcp_server()

            assert result is mcp
            mock_config.assert_called_once()
            mock_logging.assert_called_once()

    def test_create_mcp_server_with_config(self) -> None:
        """Test create_mcp_server with provided config."""
        mock_config = MagicMock()
        mock_config.otel.enabled = False

        with (
            patch("open_stocks_mcp.server.app.setup_logging") as mock_logging,
            patch("open_stocks_mcp.server.app.configure_global_rate_limiter"),
        ):
            result = create_mcp_server(mock_config)

            assert result is mcp
            mock_logging.assert_called_once_with(mock_config)


@pytest.mark.journey_system
class TestMarketToolRegistration:
    """Verify that all market and research tools remain registered after refactoring."""

    @pytest.mark.asyncio
    async def test_market_research_tools_are_registered(self) -> None:
        """Test that all 10 market/research tools are registered on the mcp server."""
        # Get the list of registered tools via list_tools method
        tools_list = await mcp.list_tools()
        tool_names = [tool.name for tool in tools_list]

        expected_tools = [
            "top_movers_sp500",
            "top_100_stocks",
            "top_movers",
            "stocks_by_tag",
            "stock_ratings",
            "stock_earnings",
            "stock_news",
            "stock_splits",
            "stock_events",
            "stock_level2_data",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"


@pytest.mark.journey_account
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
            mock_logger.warning.assert_called()
            mock_exit.assert_not_called()

    @pytest.mark.exception_test
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
            mock_logger.warning.assert_called()
            mock_exit.assert_not_called()


@pytest.mark.journey_system
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
            "unified_watchlists",
            "unified_watchlist_by_name",
            "unified_add_to_watchlist",
            "unified_remove_from_watchlist",
            "broker_comparison",
            "schwab_get_build_holdings",
            "schwab_get_day_trades",
            "schwab_get_aggregate_positions",
            "schwab_get_all_option_positions",
            "schwab_get_open_option_positions",
            "schwab_option_buy_to_open",
            "schwab_option_sell_to_close",
            "schwab_place_order",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"

    @pytest.mark.asyncio
    async def test_schwab_account_profile_tools_are_registered(self) -> None:
        """Test that the three new Schwab account/profile tools are registered."""
        tools_list = await mcp.list_tools()
        tool_names = [tool.name for tool in tools_list]

        expected_tools = [
            "schwab_get_user_preferences",
            "schwab_get_all_account_data",
            "schwab_build_user_profile",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"

    @pytest.mark.asyncio
    async def test_schwab_market_data_expansion_tools_are_registered(self) -> None:
        """Test that the four new Schwab market data expansion tools are registered."""
        tools_list = await mcp.list_tools()
        tool_names = [tool.name for tool in tools_list]

        expected_tools = [
            "schwab_get_market_hours",
            "schwab_get_movers",
            "schwab_get_movers_sp500",
            "schwab_get_instrument_by_cusip",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"

    @pytest.mark.asyncio
    async def test_schwab_trading_expansion_tools_are_registered(self) -> None:
        """Test that all 10 new Schwab trading expansion tools are registered."""
        tools_list = await mcp.list_tools()
        tool_names = [tool.name for tool in tools_list]

        expected_tools = [
            "schwab_order_sell_stop",
            "schwab_get_open_stock_orders",
            "schwab_cancel_all_stock_orders",
            "schwab_order_buy_option_limit",
            "schwab_order_sell_option_limit",
            "schwab_cancel_option_order",
            "schwab_cancel_all_option_orders",
            "schwab_order_option_credit_spread",
            "schwab_order_option_debit_spread",
            "schwab_replace_order",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"

    @pytest.mark.asyncio
    async def test_schwab_transaction_tools_are_registered(self) -> None:
        """Test that Schwab transaction tools are registered."""
        tools_list = await mcp.list_tools()
        tool_names = [tool.name for tool in tools_list]

        expected_tools = [
            "schwab_transactions",
            "schwab_transactions_by_date",
            "schwab_get_transaction",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"

    @pytest.mark.asyncio
    async def test_schwab_payment_tools_are_registered(self) -> None:
        """Test that Schwab payment tools are registered."""
        tools_list = await mcp.list_tools()
        tool_names = [tool.name for tool in tools_list]

        expected_tools = ["schwab_get_dividends", "schwab_get_interest_payments"]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"

    @pytest.mark.asyncio
    async def test_schwab_find_tradable_options_is_registered(self) -> None:
        """Test that schwab_find_tradable_options is registered as an MCP tool."""
        tools_list = await mcp.list_tools()
        tool_names = [tool.name for tool in tools_list]
        assert "schwab_find_tradable_options" in tool_names

    @pytest.mark.asyncio
    async def test_schwab_open_option_orders_is_registered(self) -> None:
        """Test that schwab_open_option_orders is registered."""
        tools_list = await mcp.list_tools()
        tool_names = [tool.name for tool in tools_list]
        assert "schwab_open_option_orders" in tool_names

    @pytest.mark.asyncio
    async def test_schwab_option_quote_tool_is_registered(self) -> None:
        """Test that schwab_option_quote is registered as an MCP tool."""
        tools_list = await mcp.list_tools()
        tool_names = [tool.name for tool in tools_list]
        assert "schwab_option_quote" in tool_names

    @pytest.mark.asyncio
    async def test_schwab_streaming_tools_are_registered(self) -> None:
        """Test that Schwab streaming tools are registered."""
        tools_list = await mcp.list_tools()
        tool_names = [tool.name for tool in tools_list]
        assert "schwab_stream_level2" in tool_names
        assert "schwab_stream_option_quotes" in tool_names
        assert "schwab_stream_level2" in tool_names
        assert "schwab_stream_account_activity" in tool_names

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

    @pytest.mark.asyncio
    async def test_health_check_tool_returns_structured_components(self) -> None:
        """Health tool should return structured component payload from service."""
        expected_health = {
            "status": "healthy",
            "components": {
                "metrics": {"status": "healthy"},
                "broker:robinhood": {"status": "healthy"},
            },
            "timestamp": "2026-01-01T00:00:00+00:00",
        }
        with patch(
            "open_stocks_mcp.server.app.get_health_check_data",
            AsyncMock(return_value={"result": expected_health}),
        ):
            result = await health_check()

        assert result == {"result": expected_health}

    @pytest.mark.asyncio
    async def test_system_tools_include_additive_broker_account_health(self) -> None:
        from open_stocks_mcp.server.app import (
            broker_status,
            metrics_summary,
            rate_limit_status,
        )

        broker = await broker_status()
        metrics = await metrics_summary()
        rate = await rate_limit_status()

        assert "broker_health" in broker["result"]
        assert "broker_health" in metrics["result"]
        assert "account_health" in metrics["result"]
        assert "endpoint_usage" in rate["result"]


def test_create_mcp_server_propagates_config_error() -> None:
    from open_stocks_mcp.config import ConfigError

    with (
        patch("open_stocks_mcp.server.app.load_config") as mock_config,
        patch("open_stocks_mcp.server.app.setup_logging") as mock_logging,
    ):
        mock_config.side_effect = ConfigError("bad config")

        with pytest.raises(ConfigError, match="bad config"):
            create_mcp_server()

        mock_logging.assert_not_called()


def test_create_mcp_server_applies_rate_limiter_from_config() -> None:
    mock_config = MagicMock()
    mock_config.otel.enabled = False
    mock_config.rate_limits.calls_per_minute = 77
    mock_config.rate_limits.calls_per_hour = 1700
    mock_config.rate_limits.burst_size = 13

    with (
        patch("open_stocks_mcp.server.app.setup_logging") as mock_logging,
        patch("open_stocks_mcp.server.app.configure_global_rate_limiter") as mock_rl,
    ):
        result = create_mcp_server(mock_config)

    assert result is mcp
    mock_logging.assert_called_once_with(mock_config)
    mock_rl.assert_called_once_with(77, 1700, 13)


@pytest.mark.asyncio
async def test_setup_brokers_skips_robinhood_when_flag_disabled() -> None:
    config = ServerConfig(brokers=BrokerSettings(enabled_brokers=["schwab"]))
    mock_registry = MagicMock()

    with (
        patch(
            "open_stocks_mcp.server.app.get_broker_registry",
            AsyncMock(return_value=mock_registry),
        ),
        patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
    ):
        await setup_brokers("user", "pass", config=config)

    mock_registry.register.assert_not_called()


@pytest.mark.asyncio
async def test_setup_brokers_registers_robinhood_when_flag_enabled() -> None:
    config = ServerConfig(brokers=BrokerSettings(enabled_brokers=["robinhood"]))
    mock_registry = MagicMock()

    with (
        patch(
            "open_stocks_mcp.server.app.get_broker_registry",
            AsyncMock(return_value=mock_registry),
        ),
        patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        patch("open_stocks_mcp.server.app.build_broker", return_value=MagicMock()),
    ):
        await setup_brokers("user", "pass", config=config)

    mock_registry.register.assert_called_once()


@pytest.mark.asyncio
async def test_setup_brokers_registers_schwab_when_enabled_and_configured() -> None:
    config = ServerConfig(
        brokers=BrokerSettings(
            enabled_brokers=["schwab"],
            schwab=SchwabConfig(api_key="key", app_secret="secret"),
        )
    )
    mock_registry = MagicMock()

    with (
        patch(
            "open_stocks_mcp.server.app.get_broker_registry",
            AsyncMock(return_value=mock_registry),
        ),
        patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        patch("open_stocks_mcp.server.app.build_broker", return_value=MagicMock()),
    ):
        await setup_brokers(None, None, config=config)

    mock_registry.register.assert_called_once()


@pytest.mark.journey_system
class TestSetupBrokers:
    """Test setup_brokers environment variable gating."""

    @pytest.mark.asyncio
    async def test_setup_brokers_default_behavior(self, monkeypatch) -> None:
        """Test default behavior (unset ENABLED_BROKERS) registers Robinhood."""
        monkeypatch.delenv("ENABLED_BROKERS", raising=False)
        mock_registry = MagicMock()
        mock_registry.register = MagicMock()

        with (
            patch(
                "open_stocks_mcp.server.app.get_broker_registry",
                AsyncMock(return_value=mock_registry),
            ),
            patch("open_stocks_mcp.server.app.build_broker", return_value=MagicMock()),
            patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        ):
            await setup_brokers("user", "pass")

        # Current behavior (and desired default): registers Robinhood if creds provided
        mock_registry.register.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_brokers_respects_enabled_brokers_schwab_only(
        self, monkeypatch
    ) -> None:
        """Test that setting ENABLED_BROKERS=schwab skips Robinhood even if creds present."""
        monkeypatch.setenv("ENABLED_BROKERS", "schwab")
        mock_registry = MagicMock()
        mock_registry.register = MagicMock()

        with (
            patch(
                "open_stocks_mcp.server.app.get_broker_registry",
                AsyncMock(return_value=mock_registry),
            ),
            patch("open_stocks_mcp.server.app.build_broker", return_value=None),
            patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        ):
            await setup_brokers("user", "pass")

        # Should NOT register anything (schwab factory returns None for unconfigured schwab)
        mock_registry.register.assert_not_called()

    @pytest.mark.asyncio
    async def test_setup_brokers_empty_enabled_brokers(self, monkeypatch) -> None:
        """Test that setting ENABLED_BROKERS='' results in no brokers."""
        monkeypatch.setenv("ENABLED_BROKERS", "")
        mock_registry = MagicMock()
        mock_registry.register = MagicMock()

        with (
            patch(
                "open_stocks_mcp.server.app.get_broker_registry",
                AsyncMock(return_value=mock_registry),
            ),
            patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        ):
            await setup_brokers("user", "pass")

        mock_registry.register.assert_not_called()

    @pytest.mark.asyncio
    async def test_setup_brokers_whitespace_and_case_insensitivity(
        self, monkeypatch
    ) -> None:
        """Test whitespace tolerance and case insensitivity in ENABLED_BROKERS."""
        monkeypatch.setenv("ENABLED_BROKERS", " Robinhood , schwab ")
        mock_registry = MagicMock()
        mock_registry.register = MagicMock()
        call_count = 0

        def _fake_build(name, ctx):
            nonlocal call_count
            if name == "robinhood":
                call_count += 1
                return MagicMock()
            return None

        with (
            patch(
                "open_stocks_mcp.server.app.get_broker_registry",
                AsyncMock(return_value=mock_registry),
            ),
            patch("open_stocks_mcp.server.app.build_broker", side_effect=_fake_build),
            patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        ):
            await setup_brokers("user", "pass")

        # Robinhood should be registered; schwab returns None (not configured)
        assert call_count == 1
        mock_registry.register.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_brokers_unknown_token_logs_warning(
        self, monkeypatch, caplog
    ) -> None:
        """Test that unknown tokens in ENABLED_BROKERS log a warning but don't crash."""
        monkeypatch.setenv("ENABLED_BROKERS", "bogus,robinhood")
        mock_registry = MagicMock()
        mock_registry.register = MagicMock()

        import logging

        caplog.set_level(logging.WARNING, logger="open_stocks_mcp")

        def _fake_build(name, ctx):
            if name == "robinhood":
                return MagicMock()
            return None

        with (
            patch(
                "open_stocks_mcp.server.app.get_broker_registry",
                AsyncMock(return_value=mock_registry),
            ),
            patch("open_stocks_mcp.server.app.build_broker", side_effect=_fake_build),
            patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        ):
            await setup_brokers("user", "pass")

        assert "bogus" in caplog.text
        # Robinhood should still be registered
        mock_registry.register.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_brokers_default_broker_valid(self, monkeypatch) -> None:
        """Test that valid DEFAULT_BROKER calls set_active_broker."""
        monkeypatch.setenv("DEFAULT_BROKER", "robinhood")
        mock_registry = MagicMock()
        mock_registry.register = MagicMock()
        mock_registry.list_brokers.return_value = ["robinhood"]

        with (
            patch(
                "open_stocks_mcp.server.app.get_broker_registry",
                AsyncMock(return_value=mock_registry),
            ),
            patch("open_stocks_mcp.server.app.build_broker", return_value=MagicMock()),
            patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        ):
            await setup_brokers("user", "pass")

        mock_registry.set_active_broker.assert_called_once_with("robinhood")

    @pytest.mark.asyncio
    async def test_setup_brokers_default_broker_invalid_logs_warning(
        self, monkeypatch, caplog
    ) -> None:
        """Test that invalid DEFAULT_BROKER logs a warning."""
        monkeypatch.setenv("DEFAULT_BROKER", "schwab")
        mock_registry = MagicMock()
        mock_registry.register = MagicMock()
        mock_registry.list_brokers.return_value = ["robinhood"]

        import logging

        caplog.set_level(logging.WARNING, logger="open_stocks_mcp")

        with (
            patch(
                "open_stocks_mcp.server.app.get_broker_registry",
                AsyncMock(return_value=mock_registry),
            ),
            patch("open_stocks_mcp.server.app.build_broker", return_value=MagicMock()),
            patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        ):
            await setup_brokers("user", "pass")

        assert "schwab" in caplog.text
        mock_registry.set_active_broker.assert_not_called()


@pytest.mark.asyncio
async def test_setup_brokers_uses_configured_robinhood_credentials() -> None:
    """setup_brokers passes config credentials in BrokerBuildContext when no CLI args."""
    config = ServerConfig(
        brokers=BrokerSettings(
            enabled_brokers=["robinhood"],
            robinhood=RobinhoodConfig(username="cfg_user", password="cfg_pass"),
        )
    )
    mock_registry = MagicMock()
    captured: list = []

    def _fake_build(name, ctx):
        captured.append(ctx)
        return MagicMock()

    with (
        patch(
            "open_stocks_mcp.server.app.get_broker_registry",
            AsyncMock(return_value=mock_registry),
        ),
        patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        patch("open_stocks_mcp.server.app.build_broker", side_effect=_fake_build),
    ):
        await setup_brokers(None, None, config=config)

    assert len(captured) == 1
    ctx = captured[0]
    # No CLI credentials provided: factory receives empty cli_credentials and must use config
    assert ctx.cli_credentials == {}
    assert ctx.config.brokers.robinhood.username == "cfg_user"
    assert ctx.config.brokers.robinhood.password == "cfg_pass"
    mock_registry.register.assert_called_once()


@pytest.mark.asyncio
async def test_setup_brokers_cli_credentials_override_config() -> None:
    """CLI username/password are placed in cli_credentials, overriding config in the factory."""
    config = ServerConfig(
        brokers=BrokerSettings(
            enabled_brokers=["robinhood"],
            robinhood=RobinhoodConfig(username="cfg_user", password="cfg_pass"),
        )
    )
    mock_registry = MagicMock()
    captured: list = []

    def _fake_build(name, ctx):
        captured.append(ctx)
        return MagicMock()

    with (
        patch(
            "open_stocks_mcp.server.app.get_broker_registry",
            AsyncMock(return_value=mock_registry),
        ),
        patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        patch("open_stocks_mcp.server.app.build_broker", side_effect=_fake_build),
    ):
        await setup_brokers("cli_user", "cli_pass", config=config)

    assert len(captured) == 1
    ctx = captured[0]
    assert ctx.cli_credentials == {"username": "cli_user", "password": "cli_pass"}


@pytest.mark.asyncio
async def test_setup_brokers_schwab_uses_broker_config_settings() -> None:
    """setup_brokers passes the full Schwab config in BrokerBuildContext."""
    config = ServerConfig(
        brokers=BrokerSettings(
            enabled_brokers=["schwab"],
            schwab=SchwabConfig(
                api_key="mykey",
                app_secret="mysecret",
                callback_url="https://my.cb/",
                token_path="/tmp/tok.json",
            ),
        )
    )
    mock_registry = MagicMock()
    captured: list = []

    def _fake_build(name, ctx):
        captured.append((name, ctx))
        return MagicMock()

    with (
        patch(
            "open_stocks_mcp.server.app.get_broker_registry",
            AsyncMock(return_value=mock_registry),
        ),
        patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        patch("open_stocks_mcp.server.app.build_broker", side_effect=_fake_build),
    ):
        await setup_brokers(None, None, config=config)

    assert len(captured) == 1
    name, ctx = captured[0]
    assert name == "schwab"
    sc = ctx.config.brokers.schwab
    assert sc.api_key == "mykey"
    assert sc.app_secret == "mysecret"
    assert sc.callback_url == "https://my.cb/"
    assert sc.token_path == "/tmp/tok.json"
    mock_registry.register.assert_called_once()


@pytest.mark.asyncio
async def test_setup_brokers_default_broker_from_config() -> None:
    """default_broker in BrokerSettings calls set_active_broker after registration."""
    config = ServerConfig(
        brokers=BrokerSettings(
            enabled_brokers=["schwab"],
            schwab=SchwabConfig(api_key="k", app_secret="s"),
            default_broker="schwab",
        )
    )
    mock_registry = MagicMock()
    mock_registry.list_brokers.return_value = ["schwab"]

    with (
        patch(
            "open_stocks_mcp.server.app.get_broker_registry",
            AsyncMock(return_value=mock_registry),
        ),
        patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        patch("open_stocks_mcp.server.app.build_broker", return_value=MagicMock()),
    ):
        await setup_brokers(None, None, config=config)

    mock_registry.set_active_broker.assert_called_once_with("schwab")


@pytest.mark.asyncio
async def test_setup_brokers_disabled_broker_skipped_even_with_creds() -> None:
    """Brokers not in enabled_brokers are not built, even if credentials exist."""
    config = ServerConfig(
        brokers=BrokerSettings(
            enabled_brokers=["schwab"],
            robinhood=RobinhoodConfig(username="u", password="p"),
            schwab=SchwabConfig(api_key="k", app_secret="s"),
        )
    )
    mock_registry = MagicMock()
    called_names: list[str] = []

    def _fake_build(name, ctx):
        called_names.append(name)
        return MagicMock()

    with (
        patch(
            "open_stocks_mcp.server.app.get_broker_registry",
            AsyncMock(return_value=mock_registry),
        ),
        patch("open_stocks_mcp.server.app.attempt_broker_logins", AsyncMock()),
        patch("open_stocks_mcp.server.app.build_broker", side_effect=_fake_build),
    ):
        await setup_brokers(None, None, config=config)

    assert "robinhood" not in called_names
    assert "schwab" in called_names


def test_main_debug_flag_passes_debug_config_to_server() -> None:
    runner = CliRunner()
    server = MagicMock()

    async def noop(*_args: object) -> None:
        return None

    server.run_stdio_async.side_effect = noop

    def fake_asyncio_run(awaitable: object) -> None:
        if inspect.iscoroutine(awaitable):
            awaitable.close()

    with (
        patch("open_stocks_mcp.server.app.create_mcp_server") as mock_create,
        patch("open_stocks_mcp.server.app.setup_brokers", side_effect=noop),
        patch("open_stocks_mcp.server.app.asyncio.run", side_effect=fake_asyncio_run),
    ):
        mock_create.return_value = server

        result = runner.invoke(main, ["--debug", "--transport", "stdio"])

    assert result.exit_code == 0
    config = mock_create.call_args.args[0]
    assert config.log_level == "DEBUG"
