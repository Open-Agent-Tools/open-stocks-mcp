"""Unit tests for Schwab options tools."""

from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.schwab_options_tools import (
    get_schwab_option_chain,
    get_schwab_option_chain_by_expiration,
    get_schwab_option_expirations,
    get_schwab_option_positions_detailed,
    get_schwab_options_positions,
    schwab_find_tradable_options,
    schwab_get_open_option_orders,
    schwab_get_option_orders,
    schwab_get_option_quote,
    schwab_option_buy_to_open,
    schwab_option_sell_to_close,
)


def _assert_retry_safe(mock_execute_broker_request: AsyncMock, expected: bool) -> None:
    call_args = mock_execute_broker_request.call_args
    assert call_args is not None
    _, kwargs = call_args
    assert kwargs.get("retry_safe") is expected


@pytest.mark.journey_options
@pytest.mark.unit
@pytest.mark.asyncio
async def test_schwab_option_buy_to_open_wrapper_delegates_to_tool() -> None:
    """Server wrapper should delegate buy-to-open to tool implementation alias."""
    from open_stocks_mcp.server import app as server_app

    expected = {"result": {"status": "order_placed", "action": "buy_to_open"}}
    with patch.object(
        server_app,
        "_schwab_option_buy_to_open_impl",
        AsyncMock(return_value=expected),
    ) as mock_execute:
        result = await server_app.schwab_option_buy_to_open(
            "abc123", "AAPL", 1, "CALL", 170.0, "2024-01-19"
        )

    mock_execute.assert_awaited_once_with(
        "abc123", "AAPL", 1, "CALL", 170.0, "2024-01-19"
    )
    assert result == expected


@pytest.mark.journey_options
@pytest.mark.unit
@pytest.mark.asyncio
async def test_schwab_option_sell_to_close_wrapper_delegates_to_tool() -> None:
    """Server wrapper should delegate sell-to-close to tool implementation alias."""
    from open_stocks_mcp.server import app as server_app

    expected = {"result": {"status": "order_placed", "action": "sell_to_close"}}
    with patch.object(
        server_app,
        "_schwab_option_sell_to_close_impl",
        AsyncMock(return_value=expected),
    ) as mock_execute:
        result = await server_app.schwab_option_sell_to_close(
            "abc123", "AAPL", 1, "PUT", 165.0, "2024-02-16"
        )

    mock_execute.assert_awaited_once_with(
        "abc123", "AAPL", 1, "PUT", 165.0, "2024-02-16"
    )
    assert result == expected


@pytest.mark.journey_options
@pytest.mark.unit
@pytest.mark.asyncio
async def test_schwab_option_order_wrappers_preserve_auth_error_response() -> None:
    """Server wrappers should preserve auth error payload shape unchanged."""
    from open_stocks_mcp.server import app as server_app

    error_response = {"result": {"error": "Not authenticated", "status": "error"}}
    with (
        patch.object(
            server_app,
            "_schwab_option_buy_to_open_impl",
            AsyncMock(return_value=error_response),
        ),
        patch.object(
            server_app,
            "_schwab_option_sell_to_close_impl",
            AsyncMock(return_value=error_response),
        ),
    ):
        buy_result = await server_app.schwab_option_buy_to_open(
            "abc123", "AAPL", 1, "CALL", 170.0, "2024-01-19"
        )
        sell_result = await server_app.schwab_option_sell_to_close(
            "abc123", "AAPL", 1, "PUT", 165.0, "2024-02-16"
        )

    assert buy_result == error_response
    assert sell_result == error_response


class TestSchwabOptionsTools:
    """Test Schwab options tools with mocked responses."""

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_get_option_chain_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful option chain retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client enums
        mock_client.Options.ContractType.CALL = "CALL"
        mock_client.Options.ContractType.PUT = "PUT"
        mock_client.Options.ContractType.ALL = "ALL"

        # Mock response
        mock_to_thread.return_value = {
            "symbol": "AAPL",
            "status": "SUCCESS",
            "underlying": {"symbol": "AAPL", "last": 175.50},
            "callExpDateMap": {
                "2024-01-19": {
                    "170.0": [
                        {
                            "putCall": "CALL",
                            "symbol": "AAPL_011924C170",
                            "description": "AAPL Jan 19 2024 170 Call",
                            "bid": 6.50,
                            "ask": 6.55,
                        }
                    ]
                }
            },
        }

        result = await get_schwab_option_chain(
            "AAPL", contract_type="call", strike_count=5
        )

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    async def test_get_option_chain_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Test option chain when authentication fails."""
        # Mock authentication error
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        result = await get_schwab_option_chain("AAPL")

        assert result == error_response

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    async def test_get_option_chain_invalid_contract_type(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Test option chain with invalid contract type."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        result = await get_schwab_option_chain("AAPL", contract_type="invalid")

        assert "result" in result
        assert "error" in result["result"]
        assert "Invalid contract_type" in result["result"]["error"]

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_get_option_chain_by_expiration_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful option chain by expiration retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client enums
        mock_client.Options.ContractType.CALL = "CALL"

        # Mock response
        mock_to_thread.return_value = {
            "symbol": "AAPL",
            "status": "SUCCESS",
            "callExpDateMap": {},
        }

        result = await get_schwab_option_chain_by_expiration(
            "AAPL", from_date="2024-01-01", to_date="2024-12-31", contract_type="call"
        )

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    async def test_get_option_expirations_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful option expirations retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock response
        mock_to_thread.return_value = {
            "expirationList": [
                {"expirationDate": "2024-01-19"},
                {"expirationDate": "2024-02-16"},
                {"expirationDate": "2024-03-15"},
            ]
        }

        result = await get_schwab_option_expirations("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert len(result["result"]["expirations"]) == 3
        assert result["result"]["count"] == 3

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    async def test_get_option_orders_filters_option_legs(
        self, mock_execute_broker_request: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Include only orders containing OPTION legs."""
        mock_get_broker.return_value = (MagicMock(), None)
        mock_execute_broker_request.return_value = [
            {
                "orderId": "opt-1",
                "orderLegCollection": [{"orderLegType": "OPTION"}],
                "status": "WORKING",
            },
            {
                "orderId": "eq-1",
                "orderLegCollection": [{"instrument": {"assetType": "EQUITY"}}],
                "status": "WORKING",
            },
        ]

        result = await schwab_get_option_orders("acct-hash")

        assert result["result"]["count"] == 1
        assert result["result"]["orders"][0]["orderId"] == "opt-1"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    async def test_get_option_orders_status_filter(
        self, mock_execute_broker_request: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Apply status filter after selecting option orders."""
        mock_get_broker.return_value = (MagicMock(), None)
        mock_execute_broker_request.return_value = [
            {
                "orderId": "filled-1",
                "orderLegCollection": [{"orderLegType": "OPTION"}],
                "status": "FILLED",
            },
            {
                "orderId": "working-1",
                "orderLegCollection": [{"instrument": {"assetType": "OPTION"}}],
                "status": "WORKING",
            },
        ]

        result = await schwab_get_option_orders("acct-hash", status="FILLED")

        assert result["result"]["count"] == 1
        assert result["result"]["orders"][0]["status"] == "FILLED"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_get_options_positions_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful options positions retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client.Account.Fields
        mock_client.Account.Fields.POSITIONS = "positions"

        # Mock response
        mock_to_thread.return_value = {
            "securitiesAccount": {
                "positions": [
                    {
                        "shortQuantity": 0.0,
                        "averagePrice": 6.50,
                        "currentDayProfitLoss": 50.0,
                        "longQuantity": 1.0,
                        "instrument": {
                            "assetType": "OPTION",
                            "symbol": "AAPL_011924C170",
                            "underlyingSymbol": "AAPL",
                            "putCall": "CALL",
                            "strikePrice": 170.0,
                            "expirationDate": "2024-01-19",
                        },
                        "marketValue": 700.0,
                    },
                    {
                        "shortQuantity": 0.0,
                        "averagePrice": 150.0,
                        "currentDayProfitLoss": -25.0,
                        "longQuantity": 10.0,
                        "instrument": {
                            "assetType": "EQUITY",
                            "symbol": "AAPL",
                        },
                        "marketValue": 1750.0,
                    },
                ]
            }
        }

        result = await get_schwab_options_positions("abc123")

        assert "result" in result
        assert "positions" in result["result"]
        assert len(result["result"]["positions"]) == 1  # Only options
        assert result["result"]["positions"][0]["symbol"] == "AAPL_011924C170"
        assert result["result"]["positions"][0]["option_type"] == "CALL"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_options_tools.option_buy_to_open_market")
    async def test_option_buy_to_open_success(
        self,
        mock_order_template: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful option buy to open order."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock order template
        mock_order_template.return_value = {"orderType": "MARKET"}

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/orders/12345"}
        mock_to_thread.return_value = mock_response

        result = await schwab_option_buy_to_open(
            "abc123", "AAPL", 1, "CALL", 170.0, "2024-01-19"
        )

        assert "result" in result
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["action"] == "buy_to_open"
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["option_type"] == "CALL"
        _assert_retry_safe(mock_to_thread, False)

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_options_tools.option_sell_to_close_market")
    async def test_option_sell_to_close_success(
        self,
        mock_order_template: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful option sell to close order."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock order template
        mock_order_template.return_value = {"orderType": "MARKET"}

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Location": "/orders/67890"}
        mock_to_thread.return_value = mock_response

        result = await schwab_option_sell_to_close(
            "abc123", "AAPL", 1, "PUT", 165.0, "2024-02-16"
        )

        assert "result" in result
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["action"] == "sell_to_close"
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["option_type"] == "PUT"
        _assert_retry_safe(mock_to_thread, False)

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.exception_test
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_get_option_chain_error(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test option chain error handling."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client enums
        mock_client.Options.ContractType.CALL = "CALL"

        # Mock API error
        mock_to_thread.side_effect = Exception("API Error")

        result = await get_schwab_option_chain("AAPL", contract_type="call")

        assert "result" in result
        assert "error" in result["result"]

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    @pytest.mark.parametrize(
        "function,args",
        [
            (get_schwab_option_chain, ("AAPL",)),
            (get_schwab_option_chain_by_expiration, ("AAPL",)),
            (get_schwab_option_expirations, ("AAPL",)),
            (get_schwab_options_positions, ("abc123",)),
            (
                schwab_option_buy_to_open,
                ("abc123", "AAPL", 1, "CALL", 175.0, "2024-01-19"),
            ),
            (
                schwab_option_sell_to_close,
                ("abc123", "AAPL", 1, "CALL", 175.0, "2024-01-19"),
            ),
        ],
    )
    async def test_options_api_failures_bulk(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        function: Callable[..., Awaitable[dict[str, Any]]],
        args: tuple[Any, ...],
    ) -> None:
        """Test various options tools for API failure responses."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.side_effect = Exception("API Error")

        result = await function(*args)
        assert result["result"]["status"] == "error"
        assert "API Error" in result["result"]["error"]
        if function in {schwab_option_buy_to_open, schwab_option_sell_to_close}:
            _assert_retry_safe(mock_to_thread, False)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_schwab_option_buy_to_open_mcp_wrapper(self) -> None:
        """Test the MCP wrapper for schwab_option_buy_to_open."""
        from unittest.mock import AsyncMock, patch

        from open_stocks_mcp.server.app import schwab_option_buy_to_open

        with patch(
            "open_stocks_mcp.server.app._schwab_option_buy_to_open_impl",
            new_callable=AsyncMock,
        ) as mock_impl:
            mock_impl.return_value = {"result": {"status": "order_placed"}}

            result = await schwab_option_buy_to_open(
                account_hash="HASH",
                symbol="AAPL",
                quantity=1,
                option_type="CALL",
                strike=150.0,
                expiration="2026-06-19",
            )

            mock_impl.assert_awaited_once_with(
                "HASH", "AAPL", 1, "CALL", 150.0, "2026-06-19"
            )
            assert result == {"result": {"status": "order_placed"}}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_schwab_option_sell_to_close_mcp_wrapper(self) -> None:
        """Test the MCP wrapper for schwab_option_sell_to_close."""
        from unittest.mock import AsyncMock, patch

        from open_stocks_mcp.server.app import schwab_option_sell_to_close

        with patch(
            "open_stocks_mcp.server.app._schwab_option_sell_to_close_impl",
            new_callable=AsyncMock,
        ) as mock_impl:
            mock_impl.return_value = {"result": {"status": "order_placed"}}

            result = await schwab_option_sell_to_close(
                account_hash="HASH",
                symbol="AAPL",
                quantity=1,
                option_type="CALL",
                strike=150.0,
                expiration="2026-06-19",
            )

            mock_impl.assert_awaited_once_with(
                "HASH", "AAPL", 1, "CALL", 150.0, "2026-06-19"
            )
            assert result == {"result": {"status": "order_placed"}}

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_get_option_positions_detailed_no_positions(
        self,
        mock_client: MagicMock,
        mock_execute: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Account.Fields.POSITIONS = "positions"
        mock_execute.return_value = {"securitiesAccount": {"positions": []}}

        result = await get_schwab_option_positions_detailed("abc123")

        assert result["result"]["positions"] == []
        assert result["result"]["count"] == 0
        assert result["result"]["enrichment_success_rate"] == "0%"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_get_option_quote_returns_contract(
        self,
        mock_client: MagicMock,
        mock_execute: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Successful lookup returns bid, ask, and putCall for the matching contract."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Options.ContractType.CALL = "CALL"

        mock_execute.return_value = {
            "symbol": "AAPL",
            "status": "SUCCESS",
            "callExpDateMap": {
                "2024-01-19:7": {
                    "170.0": [
                        {
                            "putCall": "CALL",
                            "symbol": "AAPL  240119C00170000",
                            "bid": 6.5,
                            "ask": 6.55,
                            "last": 6.52,
                            "delta": 0.54,
                            "gamma": 0.03,
                            "theta": -0.08,
                            "vega": 0.12,
                            "volatility": 0.22,
                            "openInterest": 1234,
                            "totalVolume": 56,
                        }
                    ]
                }
            },
        }

        result = await schwab_get_option_quote("AAPL", "2024-01-19", 170.0, "CALL")

        assert result["result"]["bid"] == 6.5
        assert result["result"]["ask"] == 6.55
        assert result["result"]["putCall"] == "CALL"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_get_option_quote_not_found(
        self,
        mock_client: MagicMock,
        mock_execute: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Empty chain returns an error response."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Options.ContractType.CALL = "CALL"

        mock_execute.return_value = {
            "symbol": "AAPL",
            "status": "SUCCESS",
            "callExpDateMap": {},
        }

        result = await schwab_get_option_quote("AAPL", "2024-01-19", 170.0, "CALL")

        assert result["result"]["status"] == "error"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_get_option_positions_detailed_enriches_with_quote(
        self,
        mock_client: MagicMock,
        mock_execute: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Account.Fields.POSITIONS = "positions"

        positions_response = {
            "securitiesAccount": {
                "positions": [
                    {
                        "shortQuantity": 0.0,
                        "averagePrice": 6.50,
                        "currentDayProfitLoss": 50.0,
                        "longQuantity": 1.0,
                        "instrument": {
                            "assetType": "OPTION",
                            "symbol": "AAPL  240119C00170000",
                            "underlyingSymbol": "AAPL",
                            "putCall": "CALL",
                            "strikePrice": 170.0,
                            "expirationDate": "2024-01-19",
                        },
                        "marketValue": 700.0,
                    },
                    {
                        "shortQuantity": 0.0,
                        "averagePrice": 150.0,
                        "longQuantity": 10.0,
                        "instrument": {
                            "assetType": "EQUITY",
                            "symbol": "AAPL",
                        },
                        "marketValue": 1750.0,
                    },
                ]
            }
        }

        chain_response = {
            "status": "SUCCESS",
            "symbol": "AAPL",
            "callExpDateMap": {
                "2024-01-19:5": {
                    "170.0": [
                        {
                            "symbol": "AAPL  240119C00170000",
                            "bid": 6.50,
                            "ask": 6.55,
                            "last": 6.52,
                            "mark": 6.525,
                            "greeks": {
                                "delta": 0.65,
                                "gamma": 0.03,
                                "theta": -0.05,
                                "vega": 0.12,
                            },
                        }
                    ]
                }
            },
            "putExpDateMap": {},
        }

        mock_execute.side_effect = [positions_response, chain_response]

        result = await get_schwab_option_positions_detailed("abc123")

        assert result["result"]["count"] == 1
        assert result["result"]["enrichment_success_rate"] == "100%"
        pos = result["result"]["positions"][0]
        assert pos["quote"]["bid"] == 6.50
        assert pos["quote"]["ask"] == 6.55
        assert pos["quote"]["last"] == 6.52
        assert pos["quote"]["mark"] == 6.525
        assert pos["quote"]["greeks"]["delta"] == 0.65


@pytest.mark.journey_options
@pytest.mark.unit
@pytest.mark.asyncio
@patch("open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error")
@patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
async def test_find_tradable_options_filters_by_type_and_expiration(
    mock_execute: AsyncMock,
    mock_get_broker: AsyncMock,
) -> None:
    """Filtering by call type and expiration returns only matching contracts."""
    mock_broker = MagicMock()
    mock_get_broker.return_value = (mock_broker, None)

    # Synthetic chain with calls and puts; only the AAPL_011924C170 call at 2024-01-19
    # should survive the filter for option_type="call", expiration_date="2024-01-19",
    # strike=170.0.  The put at the same expiration and the call at a different
    # expiration must be excluded.
    mock_execute.return_value = {
        "callExpDateMap": {
            "2024-01-19:30": {
                "170.0": [
                    {
                        "putCall": "CALL",
                        "symbol": "AAPL_011924C170",
                        "bid": 6.50,
                        "ask": 6.55,
                        "strikePrice": 170.0,
                    }
                ]
            },
            "2024-02-16:48": {
                "170.0": [
                    {
                        "putCall": "CALL",
                        "symbol": "AAPL_021624C170",
                        "bid": 8.00,
                        "ask": 8.10,
                        "strikePrice": 170.0,
                    }
                ]
            },
        },
        "putExpDateMap": {
            "2024-01-19:30": {
                "170.0": [
                    {
                        "putCall": "PUT",
                        "symbol": "AAPL_011924P170",
                        "bid": 2.50,
                        "ask": 2.55,
                        "strikePrice": 170.0,
                    }
                ]
            }
        },
    }

    result = await schwab_find_tradable_options(
        "AAPL", expiration_date="2024-01-19", option_type="call", strike=170.0
    )

    assert "result" in result
    data = result["result"]
    assert data["total_found"] == 1
    assert len(data["options"]) == 1
    assert data["options"][0]["symbol"] == "AAPL_011924C170"
    assert data["filters"]["option_type"] == "call"
    assert data["filters"]["expiration_date"] == "2024-01-19"
    assert data["filters"]["strike"] == 170.0


@pytest.mark.journey_options
@pytest.mark.unit
@pytest.mark.asyncio
@patch("open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error")
async def test_find_tradable_options_auth_error(mock_get_broker: AsyncMock) -> None:
    """Auth error payload is returned unchanged."""
    error_response = {"result": {"error": "Not authenticated", "status": "error"}}
    mock_get_broker.return_value = (None, error_response)

    result = await schwab_find_tradable_options("AAPL")

    assert result == error_response


@pytest.mark.journey_options
@pytest.mark.unit
@pytest.mark.asyncio
@patch("open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error")
@patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
async def test_get_open_option_orders_filters_to_working_status(
    mock_execute: AsyncMock,
    mock_get_broker: AsyncMock,
) -> None:
    """Only OPTION-legged orders in an open status should be returned."""
    mock_broker = MagicMock()
    mock_get_broker.return_value = (mock_broker, None)

    mock_execute.return_value = [
        # OPTION + WORKING → included
        {
            "status": "WORKING",
            "orderLegCollection": [
                {
                    "orderLegType": "OPTION",
                    "instrument": {"assetType": "OPTION", "symbol": "AAPL_011924C170"},
                }
            ],
        },
        # OPTION + FILLED → excluded (closed status)
        {
            "status": "FILLED",
            "orderLegCollection": [
                {
                    "orderLegType": "OPTION",
                    "instrument": {"assetType": "OPTION"},
                }
            ],
        },
        # EQUITY + WORKING → excluded (no option leg)
        {
            "status": "WORKING",
            "orderLegCollection": [
                {
                    "orderLegType": "EQUITY",
                    "instrument": {"assetType": "EQUITY", "symbol": "AAPL"},
                }
            ],
        },
    ]

    result = await schwab_get_open_option_orders("abc123")

    assert "result" in result
    assert result["result"]["count"] == 1
    orders = result["result"]["orders"]
    assert len(orders) == 1
    assert orders[0]["status"] == "WORKING"
    assert orders[0]["orderLegCollection"][0]["orderLegType"] == "OPTION"
