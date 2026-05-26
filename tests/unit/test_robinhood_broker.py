"""Unit tests for RobinhoodBroker delegation paths (no live API calls)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.brokers.base import BrokerAuthStatus
from open_stocks_mcp.brokers.robinhood import RobinhoodBroker


@pytest.fixture()
def broker() -> RobinhoodBroker:
    session_mgr = MagicMock()
    session_mgr.is_session_valid.return_value = True
    rb = RobinhoodBroker(session_manager=session_mgr)
    rb._auth_info.status = BrokerAuthStatus.AUTHENTICATED
    return rb


@pytest.fixture()
def unavailable_broker() -> RobinhoodBroker:
    session_mgr = MagicMock()
    session_mgr.is_session_valid.return_value = False
    rb = RobinhoodBroker(session_manager=session_mgr)
    rb._auth_info.status = BrokerAuthStatus.NOT_CONFIGURED
    return rb


class TestRobinhoodBrokerConstructor:
    """Constructor sets auth state based on credentials provided."""

    @pytest.mark.unit
    @pytest.mark.journey_account
    def test_both_credentials_sets_not_authenticated(self) -> None:
        session_mgr = MagicMock()
        rb = RobinhoodBroker(
            username="user@example.com",
            password="secret",
            session_manager=session_mgr,
        )
        session_mgr.set_credentials.assert_called_once_with(
            "user@example.com", "secret"
        )
        assert rb._auth_info.status == BrokerAuthStatus.NOT_AUTHENTICATED

    @pytest.mark.unit
    @pytest.mark.journey_account
    def test_only_username_sets_not_configured(self) -> None:
        session_mgr = MagicMock()
        rb = RobinhoodBroker(username="user@example.com", session_manager=session_mgr)
        assert rb._auth_info.status == BrokerAuthStatus.NOT_CONFIGURED
        assert rb._auth_info.error_message is not None
        assert "password" in rb._auth_info.error_message.lower()

    @pytest.mark.unit
    @pytest.mark.journey_account
    def test_only_password_sets_not_configured(self) -> None:
        session_mgr = MagicMock()
        rb = RobinhoodBroker(password="secret", session_manager=session_mgr)
        assert rb._auth_info.status == BrokerAuthStatus.NOT_CONFIGURED
        assert rb._auth_info.error_message is not None

    @pytest.mark.unit
    @pytest.mark.journey_account
    def test_no_credentials_sets_not_configured_with_instructions(self) -> None:
        session_mgr = MagicMock()
        rb = RobinhoodBroker(session_manager=session_mgr)
        assert rb._auth_info.status == BrokerAuthStatus.NOT_CONFIGURED
        assert rb._auth_info.setup_instructions is not None
        assert "ROBINHOOD_USERNAME" in rb._auth_info.setup_instructions

    @pytest.mark.unit
    @pytest.mark.journey_account
    def test_broker_name_is_robinhood(self) -> None:
        session_mgr = MagicMock()
        rb = RobinhoodBroker(session_manager=session_mgr)
        assert rb.name == "robinhood"


class TestRobinhoodAuthenticate:
    """authenticate() delegates to session_manager.ensure_authenticated()."""

    @pytest.mark.unit
    @pytest.mark.journey_account
    @pytest.mark.asyncio
    async def test_authenticate_success(self) -> None:
        session_mgr = MagicMock()
        session_mgr.ensure_authenticated = AsyncMock(return_value=True)
        rb = RobinhoodBroker(session_manager=session_mgr)

        result = await rb.authenticate()

        assert result is True
        assert rb._auth_info.status == BrokerAuthStatus.AUTHENTICATED
        assert rb._auth_info.last_auth_attempt is not None
        assert rb._auth_info.last_successful_auth is not None
        assert rb._auth_info.error_message is None

    @pytest.mark.unit
    @pytest.mark.journey_account
    @pytest.mark.asyncio
    async def test_authenticate_failure(self) -> None:
        session_mgr = MagicMock()
        session_mgr.ensure_authenticated = AsyncMock(return_value=False)
        rb = RobinhoodBroker(session_manager=session_mgr)

        result = await rb.authenticate()

        assert result is False
        assert rb._auth_info.status == BrokerAuthStatus.AUTH_FAILED
        assert rb._auth_info.last_auth_attempt is not None
        assert rb._auth_info.error_message is not None

    @pytest.mark.unit
    @pytest.mark.journey_account
    @pytest.mark.asyncio
    async def test_authenticate_exception(self) -> None:
        session_mgr = MagicMock()
        session_mgr.ensure_authenticated = AsyncMock(side_effect=Exception("boom"))
        rb = RobinhoodBroker(session_manager=session_mgr)

        result = await rb.authenticate()

        assert result is False
        assert rb._auth_info.status == BrokerAuthStatus.AUTH_FAILED
        assert rb._auth_info.error_message == "boom"
        assert rb._auth_info.last_auth_attempt is not None


class TestRobinhoodIsAuthenticated:
    """is_authenticated() reflects session validity and updates TOKEN_EXPIRED."""

    @pytest.mark.unit
    @pytest.mark.journey_account
    @pytest.mark.asyncio
    async def test_valid_session_returns_true(self) -> None:
        session_mgr = MagicMock()
        session_mgr.is_session_valid.return_value = True
        rb = RobinhoodBroker(session_manager=session_mgr)
        rb._auth_info.status = BrokerAuthStatus.AUTHENTICATED

        result = await rb.is_authenticated()

        assert result is True
        assert rb._auth_info.status == BrokerAuthStatus.AUTHENTICATED

    @pytest.mark.unit
    @pytest.mark.journey_account
    @pytest.mark.asyncio
    async def test_expired_session_transitions_to_token_expired(self) -> None:
        session_mgr = MagicMock()
        session_mgr.is_session_valid.return_value = False
        rb = RobinhoodBroker(session_manager=session_mgr)
        rb._auth_info.status = BrokerAuthStatus.AUTHENTICATED

        result = await rb.is_authenticated()

        assert result is False
        assert rb._auth_info.status == BrokerAuthStatus.TOKEN_EXPIRED
        assert rb._auth_info.error_message == "Session expired"

    @pytest.mark.unit
    @pytest.mark.journey_account
    @pytest.mark.asyncio
    async def test_unauthenticated_invalid_session_stays_not_authenticated(
        self,
    ) -> None:
        session_mgr = MagicMock()
        session_mgr.is_session_valid.return_value = False
        rb = RobinhoodBroker(session_manager=session_mgr)
        rb._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED

        result = await rb.is_authenticated()

        assert result is False
        assert rb._auth_info.status == BrokerAuthStatus.NOT_AUTHENTICATED


class TestRobinhoodLogout:
    """logout() clears session state and swallows exceptions."""

    @pytest.mark.unit
    @pytest.mark.journey_account
    @pytest.mark.asyncio
    async def test_logout_success_clears_status(self) -> None:
        session_mgr = MagicMock()
        session_mgr.logout = AsyncMock()
        rb = RobinhoodBroker(session_manager=session_mgr)
        rb._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        rb._auth_info.error_message = "some prior error"

        await rb.logout()

        session_mgr.logout.assert_awaited_once()
        assert rb._auth_info.status == BrokerAuthStatus.NOT_AUTHENTICATED
        assert rb._auth_info.error_message is None

    @pytest.mark.unit
    @pytest.mark.journey_account
    @pytest.mark.asyncio
    async def test_logout_exception_is_swallowed(self) -> None:
        session_mgr = MagicMock()
        session_mgr.logout = AsyncMock(side_effect=Exception("logout error"))
        rb = RobinhoodBroker(session_manager=session_mgr)
        rb._auth_info.status = BrokerAuthStatus.AUTHENTICATED

        # Must not raise
        await rb.logout()


class TestRobinhoodTradingDelegation:
    """order_buy_market / order_sell_market delegate with int(quantity)."""

    @pytest.mark.unit
    @pytest.mark.journey_trading
    @pytest.mark.asyncio
    async def test_order_buy_market_delegates_with_int_quantity(
        self, broker: RobinhoodBroker
    ) -> None:
        expected = {"result": {"order_id": "abc123", "status": "queued"}}
        with patch(
            "open_stocks_mcp.brokers.robinhood.order_buy_market",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.order_buy_market("AAPL", 3.9)

        mock_tool.assert_awaited_once_with("AAPL", 3)
        assert result == expected

    @pytest.mark.unit
    @pytest.mark.journey_trading
    @pytest.mark.asyncio
    async def test_order_sell_market_delegates_with_int_quantity(
        self, broker: RobinhoodBroker
    ) -> None:
        expected = {"result": {"order_id": "xyz789", "status": "queued"}}
        with patch(
            "open_stocks_mcp.brokers.robinhood.order_sell_market",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.order_sell_market("TSLA", 2.7)

        mock_tool.assert_awaited_once_with("TSLA", 2)
        assert result == expected

    @pytest.mark.unit
    @pytest.mark.journey_trading
    @pytest.mark.asyncio
    async def test_order_buy_market_returns_delegated_error(
        self, broker: RobinhoodBroker
    ) -> None:
        delegated_error = {"result": {"status": "error", "error": "Insufficient funds"}}
        with patch(
            "open_stocks_mcp.brokers.robinhood.order_buy_market",
            new=AsyncMock(return_value=delegated_error),
        ):
            result = await broker.order_buy_market("AAPL", 1)
        assert result == delegated_error

    @pytest.mark.unit
    @pytest.mark.journey_trading
    @pytest.mark.asyncio
    async def test_order_sell_market_returns_delegated_error(
        self, broker: RobinhoodBroker
    ) -> None:
        delegated_error = {"result": {"status": "error", "error": "Position not found"}}
        with patch(
            "open_stocks_mcp.brokers.robinhood.order_sell_market",
            new=AsyncMock(return_value=delegated_error),
        ):
            result = await broker.order_sell_market("TSLA", 1)
        assert result == delegated_error

    @pytest.mark.unit
    @pytest.mark.journey_trading
    @pytest.mark.asyncio
    async def test_order_buy_market_unavailable_returns_broker_unavailable(
        self, unavailable_broker: RobinhoodBroker
    ) -> None:
        with patch(
            "open_stocks_mcp.brokers.robinhood.order_buy_market",
            new=AsyncMock(),
        ) as mock_tool:
            result = await unavailable_broker.order_buy_market("AAPL", 1)

        mock_tool.assert_not_awaited()
        assert result["result"]["status"] == "broker_unavailable"

    @pytest.mark.unit
    @pytest.mark.journey_trading
    @pytest.mark.asyncio
    async def test_order_sell_market_unavailable_returns_broker_unavailable(
        self, unavailable_broker: RobinhoodBroker
    ) -> None:
        with patch(
            "open_stocks_mcp.brokers.robinhood.order_sell_market",
            new=AsyncMock(),
        ) as mock_tool:
            result = await unavailable_broker.order_sell_market("TSLA", 1)

        mock_tool.assert_not_awaited()
        assert result["result"]["status"] == "broker_unavailable"


class TestGetStockQuoteDelegation:
    """get_stock_quote must delegate to get_stock_price tool, not return a stub."""

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delegates_to_stock_price_tool(self, broker: RobinhoodBroker) -> None:
        expected = {"result": {"symbol": "AAPL", "price": 150.0}}
        with patch(
            "open_stocks_mcp.brokers.robinhood.get_stock_price",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.get_stock_quote("AAPL")

        mock_tool.assert_awaited_once_with("AAPL")
        assert result == expected

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_unavailable_when_not_authenticated(
        self, unavailable_broker: RobinhoodBroker
    ) -> None:
        result = await unavailable_broker.get_stock_quote("AAPL")
        assert result["result"]["status"] == "broker_unavailable"

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_is_not_not_implemented(self, broker: RobinhoodBroker) -> None:
        with patch(
            "open_stocks_mcp.brokers.robinhood.get_stock_price",
            new=AsyncMock(return_value={"result": {"price": 1.0}}),
        ):
            result = await broker.get_stock_quote("TSLA")

        assert result.get("result", {}).get("status") != "not_implemented"

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_delegated_error_response(
        self, broker: RobinhoodBroker
    ) -> None:
        """Delegated error responses are returned unchanged."""
        expected = {
            "result": {
                "status": "error",
                "error": "Invalid symbol format: 123INVALID",
            }
        }

        with patch(
            "open_stocks_mcp.brokers.robinhood.get_stock_price",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.get_stock_quote("123INVALID")

        assert result == expected
        mock_tool.assert_awaited_once_with("123INVALID")


class TestOtherRobinhoodDelegations:
    """The other Robinhood methods must also delegate cleanly without stubs."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_account_info_delegates(self, broker: RobinhoodBroker) -> None:
        expected = {"result": {"accounts": []}}
        with patch(
            "open_stocks_mcp.brokers.robinhood.get_account_info",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.get_account_info()

        mock_tool.assert_awaited_once()
        assert result == expected

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_portfolio_delegates(self, broker: RobinhoodBroker) -> None:
        expected = {"result": {"portfolio": {}}}
        with patch(
            "open_stocks_mcp.brokers.robinhood.get_portfolio",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.get_portfolio()

        mock_tool.assert_awaited_once()
        assert result == expected

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_positions_delegates(self, broker: RobinhoodBroker) -> None:
        expected = {"result": {"positions": []}}
        with patch(
            "open_stocks_mcp.brokers.robinhood.get_positions",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.get_positions()

        mock_tool.assert_awaited_once()
        assert result == expected

    @pytest.mark.journey_market_data
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_stock_price_delegates(self, broker: RobinhoodBroker) -> None:
        expected = {"result": {"price": 99.0}}
        with patch(
            "open_stocks_mcp.brokers.robinhood.get_stock_price",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.get_stock_price("GOOGL")

        mock_tool.assert_awaited_once_with("GOOGL")
        assert result == expected

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_order_buy_market_delegates(self, broker: RobinhoodBroker) -> None:
        expected = {"result": {"status": "success"}}
        with patch(
            "open_stocks_mcp.brokers.robinhood.order_buy_market",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.order_buy_market("AAPL", 1)

        mock_tool.assert_awaited_once_with("AAPL", 1)
        assert result == expected

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_order_sell_market_delegates(self, broker: RobinhoodBroker) -> None:
        expected = {"result": {"status": "success"}}
        with patch(
            "open_stocks_mcp.brokers.robinhood.order_sell_market",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await broker.order_sell_market("AAPL", 1)

        mock_tool.assert_awaited_once_with("AAPL", 1)
        assert result == expected
