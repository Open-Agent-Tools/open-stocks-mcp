"""Unit tests for cross-broker portfolio aggregation."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.brokers.base import BaseBroker, BrokerAuthStatus
from open_stocks_mcp.tools.cross_broker_tools import get_aggregated_portfolio


class MockBroker(BaseBroker):
    """Mock broker for testing."""

    def __init__(self, name: str, authenticated: bool = True):
        super().__init__(name)
        if authenticated:
            self._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        else:
            self._auth_info.status = BrokerAuthStatus.AUTH_FAILED
            self._auth_info.error_message = "Mock auth failed"

    async def authenticate(self) -> bool:
        return self._auth_info.status == BrokerAuthStatus.AUTHENTICATED

    async def is_authenticated(self) -> bool:
        return self._auth_info.status == BrokerAuthStatus.AUTHENTICATED

    async def logout(self) -> None:
        self._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED

    async def get_account_info(self):
        return {"result": {"mock": "account"}}

    async def get_portfolio(self):
        return {"result": {"mock": "portfolio"}}

    async def get_positions(self):
        return {"result": {"mock": "positions"}}

    async def get_stock_quote(self, symbol: str):
        return {"result": {"price": 100}}

    async def get_stock_price(self, symbol: str):
        return {"result": {"price": 100}}

    async def order_buy_market(self, symbol: str, quantity: float):
        return {"result": {"order": "buy"}}

    async def order_sell_market(self, symbol: str, quantity: float):
        return {"result": {"order": "sell"}}


class TestGetAggregatedPortfolio:
    """Tests for cross-broker portfolio aggregation."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.journey_portfolio
    async def test_brokers_collected_concurrently(self):
        """Broker collection runs concurrently for available brokers."""
        mock_registry = MagicMock()
        mock_registry.list_brokers.return_value = ["robinhood", "schwab"]

        rh_broker = MockBroker("robinhood", authenticated=True)
        schwab_broker = MockBroker("schwab", authenticated=True)
        mock_registry.get_broker.side_effect = lambda name: (
            rh_broker if name == "robinhood" else schwab_broker
        )

        async def _slow_rh_portfolio(*_args, **_kwargs):
            await asyncio.sleep(0.2)
            return {
                "result": {
                    "market_value": "0",
                    "equity": "0",
                    "buying_power": "0",
                    "status": "success",
                }
            }

        async def _slow_rh_positions(*_args, **_kwargs):
            await asyncio.sleep(0.2)
            return {"result": {"positions": [], "count": 0, "status": "success"}}

        async def _slow_schwab_accounts(*_args, **_kwargs):
            await asyncio.sleep(0.2)
            return {
                "result": {
                    "accounts": [
                        {
                            "securitiesAccount": {
                                "currentBalances": {
                                    "liquidationValue": 0.0,
                                    "buyingPower": 0.0,
                                },
                                "positions": [],
                            }
                        }
                    ],
                    "count": 1,
                    "status": "success",
                }
            }

        with (
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_broker_registry",
                return_value=mock_registry,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_portfolio",
                AsyncMock(side_effect=_slow_rh_portfolio),
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_positions",
                AsyncMock(side_effect=_slow_rh_positions),
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_schwab_accounts",
                AsyncMock(side_effect=_slow_schwab_accounts),
            ),
        ):
            start = time.perf_counter()
            await get_aggregated_portfolio()
            elapsed = time.perf_counter() - start

        assert elapsed < 0.35

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.journey_portfolio
    async def test_both_brokers_available(self):
        """Aggregation includes data from both brokers when both are authenticated."""
        mock_registry = MagicMock()
        mock_registry.list_brokers.return_value = ["robinhood", "schwab"]

        rh_broker = MockBroker("robinhood", authenticated=True)
        schwab_broker = MockBroker("schwab", authenticated=True)
        mock_registry.get_broker.side_effect = lambda name: (
            rh_broker if name == "robinhood" else schwab_broker
        )

        rh_portfolio = AsyncMock(
            return_value={
                "result": {
                    "market_value": "10000.00",
                    "equity": "9500.00",
                    "buying_power": "3000.00",
                    "status": "success",
                }
            }
        )
        rh_positions = AsyncMock(
            return_value={
                "result": {
                    "positions": [
                        {
                            "symbol": "AAPL",
                            "quantity": "10",
                            "average_buy_price": "150.00",
                        }
                    ],
                    "count": 1,
                    "status": "success",
                }
            }
        )
        schwab_accounts = AsyncMock(
            return_value={
                "result": {
                    "accounts": [
                        {
                            "securitiesAccount": {
                                "currentBalances": {
                                    "liquidationValue": 5000.0,
                                    "buyingPower": 2000.0,
                                },
                                "positions": [
                                    {
                                        "instrument": {"symbol": "MSFT"},
                                        "longQuantity": 5,
                                        "averagePrice": 300.0,
                                        "marketValue": 1750.0,
                                    }
                                ],
                            }
                        }
                    ],
                    "count": 1,
                    "status": "success",
                }
            }
        )

        with (
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_broker_registry",
                return_value=mock_registry,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_portfolio",
                rh_portfolio,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_positions",
                rh_positions,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_schwab_accounts",
                schwab_accounts,
            ),
        ):
            result = await get_aggregated_portfolio()

        assert "result" in result
        data = result["result"]
        assert data["status"] == "success"
        assert "brokers" in data
        assert "aggregated" in data
        assert "robinhood" in data["brokers"]
        assert "schwab" in data["brokers"]
        assert data["brokers"]["robinhood"]["status"] == "available"
        assert data["brokers"]["schwab"]["status"] == "available"
        assert data["partial_failure"] is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.journey_portfolio
    async def test_schwab_unavailable_returns_degraded_response(self):
        """Aggregation returns degraded response when Schwab is not authenticated."""
        mock_registry = MagicMock()
        mock_registry.list_brokers.return_value = ["robinhood", "schwab"]

        rh_broker = MockBroker("robinhood", authenticated=True)
        schwab_broker = MockBroker("schwab", authenticated=False)
        mock_registry.get_broker.side_effect = lambda name: (
            rh_broker if name == "robinhood" else schwab_broker
        )

        rh_portfolio = AsyncMock(
            return_value={
                "result": {
                    "market_value": "10000.00",
                    "equity": "9500.00",
                    "buying_power": "3000.00",
                    "status": "success",
                }
            }
        )
        rh_positions = AsyncMock(
            return_value={
                "result": {
                    "positions": [
                        {
                            "symbol": "AAPL",
                            "quantity": "10",
                            "average_buy_price": "150.00",
                        }
                    ],
                    "count": 1,
                    "status": "success",
                }
            }
        )

        with (
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_broker_registry",
                return_value=mock_registry,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_portfolio",
                rh_portfolio,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_positions",
                rh_positions,
            ),
        ):
            result = await get_aggregated_portfolio()

        assert "result" in result
        data = result["result"]
        assert data["status"] == "success"
        assert data["partial_failure"] is True
        assert "schwab" in data["unavailable_brokers"]
        assert data["brokers"]["robinhood"]["status"] == "available"
        assert data["brokers"]["schwab"]["status"] == "unavailable"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.journey_portfolio
    async def test_robinhood_unavailable_returns_degraded_response(self):
        """Aggregation returns degraded response when Robinhood is not authenticated."""
        mock_registry = MagicMock()
        mock_registry.list_brokers.return_value = ["robinhood", "schwab"]

        rh_broker = MockBroker("robinhood", authenticated=False)
        schwab_broker = MockBroker("schwab", authenticated=True)
        mock_registry.get_broker.side_effect = lambda name: (
            rh_broker if name == "robinhood" else schwab_broker
        )

        schwab_accounts = AsyncMock(
            return_value={
                "result": {
                    "accounts": [
                        {
                            "securitiesAccount": {
                                "currentBalances": {
                                    "liquidationValue": 5000.0,
                                    "buyingPower": 2000.0,
                                },
                                "positions": [],
                            }
                        }
                    ],
                    "count": 1,
                    "status": "success",
                }
            }
        )

        with (
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_broker_registry",
                return_value=mock_registry,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_schwab_accounts",
                schwab_accounts,
            ),
        ):
            result = await get_aggregated_portfolio()

        assert "result" in result
        data = result["result"]
        assert data["status"] == "success"
        assert data["partial_failure"] is True
        assert "robinhood" in data["unavailable_brokers"]
        assert data["brokers"]["robinhood"]["status"] == "unavailable"
        assert data["brokers"]["schwab"]["status"] == "available"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.journey_portfolio
    async def test_both_brokers_unavailable(self):
        """Aggregation returns degraded response when all brokers are unavailable."""
        mock_registry = MagicMock()
        mock_registry.list_brokers.return_value = ["robinhood", "schwab"]

        rh_broker = MockBroker("robinhood", authenticated=False)
        schwab_broker = MockBroker("schwab", authenticated=False)
        mock_registry.get_broker.side_effect = lambda name: (
            rh_broker if name == "robinhood" else schwab_broker
        )

        with patch(
            "open_stocks_mcp.tools.cross_broker_tools.get_broker_registry",
            return_value=mock_registry,
        ):
            result = await get_aggregated_portfolio()

        assert "result" in result
        data = result["result"]
        assert data["status"] == "success"
        assert data["partial_failure"] is True
        assert set(data["unavailable_brokers"]) == {"robinhood", "schwab"}
        assert data["brokers"]["robinhood"]["status"] == "unavailable"
        assert data["brokers"]["schwab"]["status"] == "unavailable"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.journey_portfolio
    async def test_aggregated_totals_sum_both_brokers(self):
        """Aggregated totals correctly sum values from both brokers."""
        mock_registry = MagicMock()
        mock_registry.list_brokers.return_value = ["robinhood", "schwab"]

        rh_broker = MockBroker("robinhood", authenticated=True)
        schwab_broker = MockBroker("schwab", authenticated=True)
        mock_registry.get_broker.side_effect = lambda name: (
            rh_broker if name == "robinhood" else schwab_broker
        )

        rh_portfolio = AsyncMock(
            return_value={
                "result": {
                    "market_value": "10000.00",
                    "equity": "9500.00",
                    "buying_power": "3000.00",
                    "status": "success",
                }
            }
        )
        rh_positions = AsyncMock(
            return_value={"result": {"positions": [], "count": 0, "status": "success"}}
        )
        schwab_accounts = AsyncMock(
            return_value={
                "result": {
                    "accounts": [
                        {
                            "securitiesAccount": {
                                "currentBalances": {
                                    "liquidationValue": 5000.0,
                                    "buyingPower": 2000.0,
                                },
                                "positions": [],
                            }
                        }
                    ],
                    "count": 1,
                    "status": "success",
                }
            }
        )

        with (
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_broker_registry",
                return_value=mock_registry,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_portfolio",
                rh_portfolio,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_positions",
                rh_positions,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_schwab_accounts",
                schwab_accounts,
            ),
        ):
            result = await get_aggregated_portfolio()

        data = result["result"]
        aggregated = data["aggregated"]

        # RH: market_value=10000, buying_power=3000; Schwab: market_value=5000, buying_power=2000
        assert aggregated["total_market_value"] == pytest.approx(15000.0)
        assert aggregated["total_buying_power"] == pytest.approx(5000.0)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.journey_portfolio
    async def test_positions_merged_from_both_brokers(self):
        """Aggregated positions list includes entries from both brokers."""
        mock_registry = MagicMock()
        mock_registry.list_brokers.return_value = ["robinhood", "schwab"]

        rh_broker = MockBroker("robinhood", authenticated=True)
        schwab_broker = MockBroker("schwab", authenticated=True)
        mock_registry.get_broker.side_effect = lambda name: (
            rh_broker if name == "robinhood" else schwab_broker
        )

        rh_portfolio = AsyncMock(
            return_value={
                "result": {
                    "market_value": "10000.00",
                    "equity": "9500.00",
                    "buying_power": "3000.00",
                    "status": "success",
                }
            }
        )
        rh_positions = AsyncMock(
            return_value={
                "result": {
                    "positions": [
                        {
                            "symbol": "AAPL",
                            "quantity": "10",
                            "average_buy_price": "150.00",
                        }
                    ],
                    "count": 1,
                    "status": "success",
                }
            }
        )
        schwab_accounts = AsyncMock(
            return_value={
                "result": {
                    "accounts": [
                        {
                            "securitiesAccount": {
                                "currentBalances": {
                                    "liquidationValue": 5000.0,
                                    "buyingPower": 2000.0,
                                },
                                "positions": [
                                    {
                                        "instrument": {"symbol": "MSFT"},
                                        "longQuantity": 5,
                                        "averagePrice": 300.0,
                                        "marketValue": 1750.0,
                                    }
                                ],
                            }
                        }
                    ],
                    "count": 1,
                    "status": "success",
                }
            }
        )

        with (
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_broker_registry",
                return_value=mock_registry,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_portfolio",
                rh_portfolio,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_positions",
                rh_positions,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_schwab_accounts",
                schwab_accounts,
            ),
        ):
            result = await get_aggregated_portfolio()

        data = result["result"]
        symbols = {p["symbol"] for p in data["aggregated"]["positions"]}
        assert "AAPL" in symbols
        assert "MSFT" in symbols

        # Each position tagged with source broker
        for pos in data["aggregated"]["positions"]:
            assert "broker" in pos

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.journey_portfolio
    async def test_broker_status_includes_auth_error_message(self):
        """Unavailable broker entry includes the auth error reason."""
        mock_registry = MagicMock()
        mock_registry.list_brokers.return_value = ["robinhood", "schwab"]

        rh_broker = MockBroker("robinhood", authenticated=True)
        schwab_broker = MockBroker("schwab", authenticated=False)
        mock_registry.get_broker.side_effect = lambda name: (
            rh_broker if name == "robinhood" else schwab_broker
        )

        rh_portfolio = AsyncMock(
            return_value={
                "result": {
                    "market_value": "10000.00",
                    "equity": "9500.00",
                    "buying_power": "3000.00",
                    "status": "success",
                }
            }
        )
        rh_positions = AsyncMock(
            return_value={"result": {"positions": [], "count": 0, "status": "success"}}
        )

        with (
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_broker_registry",
                return_value=mock_registry,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_portfolio",
                rh_portfolio,
            ),
            patch(
                "open_stocks_mcp.tools.cross_broker_tools.get_positions",
                rh_positions,
            ),
        ):
            result = await get_aggregated_portfolio()

        schwab_entry = result["result"]["brokers"]["schwab"]
        assert "error" in schwab_entry
        assert schwab_entry["error"] is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.journey_portfolio
    async def test_no_brokers_registered(self):
        """Empty registry returns empty aggregation without error."""
        mock_registry = MagicMock()
        mock_registry.list_brokers.return_value = []

        with patch(
            "open_stocks_mcp.tools.cross_broker_tools.get_broker_registry",
            return_value=mock_registry,
        ):
            result = await get_aggregated_portfolio()

        assert "result" in result
        data = result["result"]
        assert data["status"] == "success"
        assert data["aggregated"]["total_market_value"] == 0.0
        assert data["aggregated"]["positions"] == []
        assert data["partial_failure"] is False
