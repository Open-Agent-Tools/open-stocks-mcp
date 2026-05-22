"""Unit tests for Schwab options tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.schwab_options_tools import (
    get_schwab_option_chain,
    get_schwab_option_chain_by_expiration,
    get_schwab_option_expirations,
    get_schwab_options_positions,
    schwab_find_tradable_options,
    schwab_get_open_option_orders,
    schwab_get_option_orders,
    schwab_get_option_positions_detailed,
    schwab_get_option_quote,
    schwab_option_buy_to_open,
    schwab_option_sell_to_close,
)


def _assert_retry_safe(mock_execute_broker_request: AsyncMock, expected: bool) -> None:
    call_args = mock_execute_broker_request.call_args
    assert call_args is not None
    _, kwargs = call_args
    assert kwargs.get("retry_safe") is expected


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
        function,
        args,
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

    # ---- schwab_find_tradable_options ----------------------------------

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_find_tradable_options_filters_by_type_and_expiration(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Filter to calls at a specific expiration only."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_client.Options.ContractType.CALL = "CALL"
        mock_client.Options.ContractType.PUT = "PUT"
        mock_client.Options.ContractType.ALL = "ALL"

        mock_to_thread.return_value = {
            "callExpDateMap": {
                "2024-01-19:30": {
                    "170.0": [
                        {
                            "putCall": "CALL",
                            "symbol": "AAPL_011924C170",
                            "bid": 6.50,
                            "ask": 6.55,
                        }
                    ],
                    "175.0": [
                        {
                            "putCall": "CALL",
                            "symbol": "AAPL_011924C175",
                            "bid": 4.10,
                            "ask": 4.15,
                        }
                    ],
                }
            },
            "putExpDateMap": {
                "2024-01-19:30": {
                    "170.0": [
                        {
                            "putCall": "PUT",
                            "symbol": "AAPL_011924P170",
                            "bid": 3.20,
                            "ask": 3.25,
                        }
                    ],
                }
            },
        }

        result = await schwab_find_tradable_options(
            "AAPL", expiration_date="2024-01-19", option_type="call"
        )

        assert "result" in result
        options = result["result"]["options"]
        assert len(options) == 2
        assert {opt["putCall"] for opt in options} == {"CALL"}
        assert result["result"]["total_found"] == 2
        assert result["result"]["filters"]["option_type"] == "CALL"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_find_tradable_options_strike_filter(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Strike filter narrows the returned contracts."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Options.ContractType.CALL = "CALL"
        mock_client.Options.ContractType.PUT = "PUT"
        mock_client.Options.ContractType.ALL = "ALL"

        mock_to_thread.return_value = {
            "callExpDateMap": {
                "2024-01-19:30": {
                    "170.0": [{"putCall": "CALL", "symbol": "C170"}],
                    "175.0": [{"putCall": "CALL", "symbol": "C175"}],
                }
            },
            "putExpDateMap": {},
        }

        result = await schwab_find_tradable_options("AAPL", strike=170.0)

        assert result["result"]["total_found"] == 1
        assert result["result"]["options"][0]["symbol"] == "C170"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    async def test_find_tradable_options_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Auth failures short-circuit and return the error tuple."""
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        result = await schwab_find_tradable_options("AAPL")

        assert result == error_response

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    async def test_find_tradable_options_invalid_option_type(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Invalid option_type is rejected before any API call."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        result = await schwab_find_tradable_options("AAPL", option_type="bogus")

        assert result["result"]["status"] == "error"
        assert "Invalid option_type" in result["result"]["error"]

    # ---- schwab_get_option_positions_detailed --------------------------

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
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Each open option position is enriched with a quote sub-dict."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_client.Account.Fields.POSITIONS = "positions"
        mock_client.Options.ContractType.CALL = "CALL"
        mock_client.Options.ContractType.PUT = "PUT"

        account_payload = {
            "securitiesAccount": {
                "positions": [
                    {
                        "shortQuantity": 0.0,
                        "averagePrice": 6.50,
                        "longQuantity": 1.0,
                        "currentDayProfitLoss": 50.0,
                        "instrument": {
                            "assetType": "OPTION",
                            "symbol": "AAPL_011924C170",
                            "underlyingSymbol": "AAPL",
                            "putCall": "CALL",
                            "strikePrice": 170.0,
                            "expirationDate": "2024-01-19T00:00:00.000Z",
                        },
                        "marketValue": 700.0,
                    }
                ]
            }
        }
        chain_payload = {
            "callExpDateMap": {
                "2024-01-19:30": {
                    "170.0": [
                        {
                            "putCall": "CALL",
                            "bid": 6.60,
                            "ask": 6.70,
                            "last": 6.65,
                            "mark": 6.65,
                            "delta": 0.55,
                        }
                    ]
                }
            }
        }
        mock_to_thread.side_effect = [account_payload, chain_payload]

        result = await schwab_get_option_positions_detailed("abc123")

        assert "result" in result
        positions = result["result"]["positions"]
        assert len(positions) == 1
        quote = positions[0]["quote"]
        assert quote["bid"] == 6.60
        assert quote["ask"] == 6.70
        assert quote["last"] == 6.65
        assert result["result"]["enrichment_success_rate"] == "100%"

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
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Empty positions returns count=0 and 0% enrichment."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Account.Fields.POSITIONS = "positions"

        mock_to_thread.return_value = {"securitiesAccount": {"positions": []}}

        result = await schwab_get_option_positions_detailed("abc123")

        assert result["result"]["count"] == 0
        assert result["result"]["enrichment_success_rate"] == "0%"
        assert result["result"]["positions"] == []

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    async def test_get_option_positions_detailed_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        result = await schwab_get_option_positions_detailed("abc123")

        assert result == error_response

    # ---- schwab_get_option_quote ---------------------------------------

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
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Single contract lookup returns the requested contract dict."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Options.ContractType.CALL = "CALL"

        mock_to_thread.return_value = {
            "callExpDateMap": {
                "2024-01-19:30": {
                    "170.0": [
                        {
                            "putCall": "CALL",
                            "symbol": "AAPL_011924C170",
                            "bid": 6.50,
                            "ask": 6.55,
                            "last": 6.52,
                            "delta": 0.55,
                        }
                    ]
                }
            }
        }

        result = await schwab_get_option_quote(
            "AAPL", "2024-01-19", 170.0, "call"
        )

        assert "result" in result
        assert result["result"]["putCall"] == "CALL"
        assert result["result"]["bid"] == 6.50
        assert result["result"]["ask"] == 6.55

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
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Empty chain map produces an error response."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Options.ContractType.CALL = "CALL"

        mock_to_thread.return_value = {"callExpDateMap": {}, "putExpDateMap": {}}

        result = await schwab_get_option_quote(
            "AAPL", "2024-01-19", 170.0, "call"
        )

        assert result["result"]["status"] == "error"
        assert "No CALL contract" in result["result"]["error"]

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    async def test_get_option_quote_invalid_type(
        self, mock_get_broker: AsyncMock
    ) -> None:
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        result = await schwab_get_option_quote(
            "AAPL", "2024-01-19", 170.0, "spread"
        )

        assert result["result"]["status"] == "error"
        assert "Invalid option_type" in result["result"]["error"]

    # ---- schwab_get_option_orders --------------------------------------

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    async def test_get_option_orders_filters_option_legs(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Only option-legged orders are returned."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_to_thread.return_value = [
            {
                "orderId": "1",
                "status": "FILLED",
                "orderLegCollection": [{"orderLegType": "OPTION"}],
            },
            {
                "orderId": "2",
                "status": "FILLED",
                "orderLegCollection": [{"orderLegType": "EQUITY"}],
            },
            {
                "orderId": "3",
                "status": "WORKING",
                "orderLegCollection": [
                    {"instrument": {"assetType": "OPTION"}},
                ],
            },
        ]

        result = await schwab_get_option_orders("abc123")

        assert result["result"]["count"] == 2
        ids = [o["orderId"] for o in result["result"]["orders"]]
        assert ids == ["1", "3"]

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    async def test_get_option_orders_status_filter(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """status='FILLED' excludes orders in other states."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_to_thread.return_value = [
            {
                "orderId": "1",
                "status": "FILLED",
                "orderLegCollection": [{"orderLegType": "OPTION"}],
            },
            {
                "orderId": "2",
                "status": "WORKING",
                "orderLegCollection": [{"orderLegType": "OPTION"}],
            },
        ]

        result = await schwab_get_option_orders("abc123", status="FILLED")

        assert result["result"]["count"] == 1
        assert result["result"]["orders"][0]["orderId"] == "1"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    async def test_get_option_orders_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        result = await schwab_get_option_orders("abc123")

        assert result == error_response

    # ---- schwab_get_open_option_orders ---------------------------------

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_options_tools.execute_broker_request")
    async def test_get_open_option_orders_filters_to_working_status(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Only OPTION-legged + open-status orders are returned."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_to_thread.return_value = [
            {
                "orderId": "1",
                "status": "WORKING",
                "orderLegCollection": [{"orderLegType": "OPTION"}],
            },
            {
                "orderId": "2",
                "status": "FILLED",
                "orderLegCollection": [{"orderLegType": "OPTION"}],
            },
            {
                "orderId": "3",
                "status": "WORKING",
                "orderLegCollection": [{"orderLegType": "EQUITY"}],
            },
            {
                "orderId": "4",
                "status": "PENDING_ACTIVATION",
                "orderLegCollection": [
                    {"instrument": {"assetType": "OPTION"}},
                ],
            },
        ]

        result = await schwab_get_open_option_orders("abc123")

        assert result["result"]["count"] == 2
        ids = [o["orderId"] for o in result["result"]["orders"]]
        assert ids == ["1", "4"]

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error"
    )
    async def test_get_open_option_orders_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        result = await schwab_get_open_option_orders("abc123")

        assert result == error_response
