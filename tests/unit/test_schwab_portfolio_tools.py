"""Unit tests for computed Schwab portfolio tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.schwab_portfolio_tools import (
    get_schwab_aggregate_positions,
    get_schwab_all_option_positions,
    get_schwab_build_holdings,
    get_schwab_day_trades,
    get_schwab_open_option_positions,
)


@pytest.mark.journey_portfolio
@pytest.mark.unit
class TestSchwabPortfolioTools:
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_portfolio_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_portfolio_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_portfolio_tools.Client")
    async def test_schwab_get_build_holdings_enriches_positions_with_quotes(
        self,
        mock_client: MagicMock,
        mock_execute_broker_request: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Account.Fields.POSITIONS = "positions"

        accounts_payload = [
            {
                "securitiesAccount": {
                    "hashValue": "hash-1",
                    "positions": [
                        {
                            "longQuantity": 10,
                            "shortQuantity": 0,
                            "averagePrice": 100.0,
                            "marketValue": 1100.0,
                            "instrument": {"symbol": "AAPL", "assetType": "EQUITY"},
                        }
                    ],
                }
            }
        ]
        quotes_payload = {
            "AAPL": {"quote": {"lastPrice": 110.0, "netChange": 2.0}},
        }
        mock_execute_broker_request.side_effect = [accounts_payload, quotes_payload]

        result = await get_schwab_build_holdings()

        assert result["result"]["status"] == "ok"
        assert result["result"]["total_positions"] == 1
        assert result["result"]["holdings"]["AAPL"]["price"] == 110.0
        assert result["result"]["holdings"]["AAPL"]["quantity"] == 10.0

    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_portfolio_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_portfolio_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_portfolio_tools.Client")
    async def test_schwab_get_day_trades_counts_same_day_trade_pairs(
        self,
        mock_client: MagicMock,
        mock_execute_broker_request: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Transactions.TransactionType.TRADE = "TRADE"

        accounts_payload = [{"hashValue": "hash-1"}]
        trades_payload = [
            {"symbol": "AAPL", "transactionDate": "2026-01-01T10:00:00Z", "instruction": "BUY"},
            {"symbol": "AAPL", "transactionDate": "2026-01-01T11:00:00Z", "instruction": "SELL"},
            {"symbol": "MSFT", "transactionDate": "2026-01-01T11:00:00Z", "instruction": "BUY"},
            {"symbol": "AAPL", "transactionDate": "2026-01-02T11:00:00Z", "instruction": "BUY"},
        ]
        mock_execute_broker_request.side_effect = [accounts_payload, trades_payload]

        result = await get_schwab_day_trades()

        assert result["result"]["status"] == "ok"
        assert result["result"]["day_trade_count"] == 1
        assert result["result"]["remaining_day_trades"] == 2
        assert result["result"]["pattern_day_trader"] is False

    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_portfolio_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_portfolio_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_portfolio_tools.Client")
    async def test_schwab_get_aggregate_positions_sums_matching_symbols_across_accounts(
        self,
        mock_client: MagicMock,
        mock_execute_broker_request: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Account.Fields.POSITIONS = "positions"

        accounts_payload = [
            {
                "securitiesAccount": {
                    "hashValue": "hash-1",
                    "positions": [
                        {
                            "longQuantity": 5,
                            "shortQuantity": 0,
                            "marketValue": 500.0,
                            "currentDayProfitLoss": 5.0,
                            "instrument": {"symbol": "AAPL", "assetType": "EQUITY"},
                        }
                    ],
                }
            },
            {
                "securitiesAccount": {
                    "hashValue": "hash-2",
                    "positions": [
                        {
                            "longQuantity": 3,
                            "shortQuantity": 0,
                            "marketValue": 300.0,
                            "currentDayProfitLoss": 3.0,
                            "instrument": {"symbol": "AAPL", "assetType": "EQUITY"},
                        },
                        {
                            "longQuantity": 2,
                            "shortQuantity": 0,
                            "marketValue": 200.0,
                            "currentDayProfitLoss": 2.0,
                            "instrument": {"symbol": "TSLA", "assetType": "EQUITY"},
                        },
                    ],
                }
            },
        ]
        mock_execute_broker_request.return_value = accounts_payload

        result = await get_schwab_aggregate_positions()

        assert result["result"]["status"] == "ok"
        assert result["result"]["count"] == 2
        by_symbol = {item["symbol"]: item for item in result["result"]["positions"]}
        assert by_symbol["AAPL"]["net_quantity"] == 8.0
        assert by_symbol["AAPL"]["market_value"] == 800.0

    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_portfolio_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_portfolio_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_portfolio_tools.Client")
    async def test_schwab_get_all_option_positions_filters_option_asset_type_across_accounts(
        self,
        mock_client: MagicMock,
        mock_execute_broker_request: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Account.Fields.POSITIONS = "positions"

        accounts_payload = [
            {
                "securitiesAccount": {
                    "hashValue": "hash-1",
                    "positions": [
                        {
                            "longQuantity": 1,
                            "shortQuantity": 0,
                            "marketValue": 200.0,
                            "instrument": {
                                "symbol": "AAPL_011926C150",
                                "assetType": "OPTION",
                                "putCall": "CALL",
                            },
                        },
                        {
                            "longQuantity": 1,
                            "shortQuantity": 0,
                            "marketValue": 150.0,
                            "instrument": {"symbol": "AAPL", "assetType": "EQUITY"},
                        },
                    ],
                }
            }
        ]
        mock_execute_broker_request.side_effect = [accounts_payload, accounts_payload]

        result = await get_schwab_all_option_positions()

        assert result["result"]["status"] == "ok"
        assert result["result"]["total_positions"] == 1
        assert result["result"]["positions"][0]["symbol"] == "AAPL_011926C150"

    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_portfolio_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_portfolio_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_portfolio_tools.Client")
    async def test_schwab_get_open_option_positions_returns_only_nonzero_option_quantity(
        self,
        mock_client: MagicMock,
        mock_execute_broker_request: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Account.Fields.POSITIONS = "positions"

        accounts_payload = [
            {
                "securitiesAccount": {
                    "hashValue": "hash-1",
                    "positions": [
                        {
                            "longQuantity": 2,
                            "shortQuantity": 0,
                            "marketValue": 200.0,
                            "instrument": {
                                "symbol": "AAPL_011926C150",
                                "assetType": "OPTION",
                                "putCall": "CALL",
                            },
                        },
                        {
                            "longQuantity": 0,
                            "shortQuantity": 0,
                            "marketValue": 0.0,
                            "instrument": {
                                "symbol": "AAPL_011926P100",
                                "assetType": "OPTION",
                                "putCall": "PUT",
                            },
                        },
                    ],
                }
            }
        ]
        mock_execute_broker_request.side_effect = [
            accounts_payload,
            accounts_payload,
            accounts_payload,
        ]

        result = await get_schwab_open_option_positions()

        assert result["result"]["status"] == "ok"
        assert result["result"]["total_positions"] == 1
        assert result["result"]["positions"][0]["symbol"] == "AAPL_011926C150"
