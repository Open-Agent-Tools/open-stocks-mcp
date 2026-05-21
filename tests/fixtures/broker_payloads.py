"""Shared representative broker API payloads for unit tests."""

from copy import deepcopy
from typing import Any


def _copy(payload: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(payload)


def _copy_list(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return deepcopy(payload)


def robinhood_quote_payload() -> dict[str, Any]:
    """Return a representative Robinhood quote payload."""
    return _copy(
        {
            "symbol": "AAPL",
            "previous_close": "148.50",
            "volume": "1000000",
            "ask_price": "150.30",
            "bid_price": "150.20",
            "last_trade_price": "150.25",
            "last_extended_hours_trade_price": "150.18",
            "previous_close_date": "2023-12-29",
            "trading_halted": False,
            "has_traded": True,
            "last_trade_price_source": "consolidated",
            "updated_at": "2023-12-30T20:59:59.000000Z",
            "instrument": (
                "https://robinhood.com/instruments/"
                "450dfc6d-5510-4d40-abfb-f633b7d9be3e/"
            ),
        }
    )


def robinhood_fundamentals_payload() -> dict[str, Any]:
    """Return representative Robinhood fundamental data."""
    return _copy(
        {
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "description": "Apple Inc. designs and manufactures smartphones",
            "market_cap": "3000000000000",
            "pe_ratio": "25.5",
            "dividend_yield": "0.50",
            "high_52_weeks": "182.94",
            "low_52_weeks": "124.17",
            "average_volume": "50000000",
        }
    )


def robinhood_instrument_payload() -> dict[str, Any]:
    """Return representative Robinhood instrument metadata."""
    return _copy(
        {
            "symbol": "AAPL",
            "simple_name": "Apple Inc.",
            "name": "Apple Inc.",
            "tradeable": True,
            "country": "US",
            "type": "stock",
            "id": "450dfc6d-5510-4d40-abfb-f633b7d9be3e",
            "url": (
                "https://robinhood.com/instruments/"
                "450dfc6d-5510-4d40-abfb-f633b7d9be3e/"
            ),
            "market": "NASDAQ",
            "list_date": "1980-12-12",
            "state": "active",
            "tradability": "tradable",
        }
    )


def robinhood_search_payload() -> list[dict[str, Any]]:
    """Return representative Robinhood instrument search results."""
    return _copy_list(
        [
            robinhood_instrument_payload(),
            {
                "symbol": "GOOGL",
                "simple_name": "Alphabet Inc.",
                "name": "Alphabet Inc.",
                "tradeable": True,
                "country": "US",
                "type": "stock",
                "id": "943c5009-a0bb-4665-8cf4-a95dab5874e4",
                "url": (
                    "https://robinhood.com/instruments/"
                    "943c5009-a0bb-4665-8cf4-a95dab5874e4/"
                ),
            },
        ]
    )


def robinhood_user_profile_payload() -> dict[str, Any]:
    """Return representative Robinhood user profile data."""
    return _copy(
        {
            "username": "testuser",
            "created_at": "2023-01-01T00:00:00Z",
        }
    )


def robinhood_portfolio_payload() -> dict[str, Any]:
    """Return representative Robinhood portfolio profile data."""
    return _copy(
        {
            "total_return_today": "50.00",
            "total_return_today_percent": "2.50",
            "market_value": "2000.00",
            "equity": "2100.00",
            "buying_power": "100.00",
        }
    )


def robinhood_positions_payload() -> list[dict[str, Any]]:
    """Return representative Robinhood open stock positions."""
    return _copy_list(
        [
            {
                "instrument": "https://robinhood.com/instruments/aapl123/",
                "quantity": "10.0000",
                "average_buy_price": "150.00",
                "updated_at": "2023-01-01T00:00:00Z",
            },
            {
                "instrument": "https://robinhood.com/instruments/googl456/",
                "quantity": "5.0000",
                "average_buy_price": "2500.00",
                "updated_at": "2023-01-01T00:00:00Z",
            },
        ]
    )


def robinhood_phoenix_account_payload() -> dict[str, Any]:
    """Return representative Robinhood phoenix account details."""
    def currency(amount: str) -> dict[str, str]:
        return {"amount": amount, "currency_code": "USD", "currency_id": "usd"}

    return _copy(
        {
            "results": [
                {
                    "portfolio_equity": currency("2100.00"),
                    "total_equity": currency("2100.00"),
                    "account_buying_power": currency("1000.00"),
                    "options_buying_power": currency("1000.00"),
                    "crypto_buying_power": currency("1000.00"),
                    "uninvested_cash": currency("100.00"),
                    "withdrawable_cash": currency("100.00"),
                    "cash_available_from_instant_deposits": currency("0.00"),
                    "cash_held_for_orders": currency("0.00"),
                    "near_margin_call": False,
                }
            ]
        }
    )


def robinhood_build_holdings_payload() -> dict[str, Any]:
    """Return representative Robinhood build_holdings output."""
    return _copy(
        {
            "AAPL": {
                "price": "150.00",
                "quantity": "10",
                "average_buy_price": "145.00",
                "equity": "1500.00",
                "percent_change": "3.45",
                "equity_change": "50.00",
                "type": "stock",
                "name": "Apple Inc",
                "pe_ratio": "25.5",
                "percentage": "15.2",
            },
            "GOOGL": {
                "price": "2800.00",
                "quantity": "5",
                "average_buy_price": "2700.00",
                "equity": "14000.00",
                "percent_change": "3.70",
                "equity_change": "500.00",
                "type": "stock",
                "name": "Alphabet Inc",
                "pe_ratio": "28.3",
                "percentage": "84.8",
            },
        }
    )


def schwab_quote_payload() -> dict[str, Any]:
    """Return a representative Schwab quote response."""
    return _copy(
        {
            "AAPL": {
                "assetMainType": "EQUITY",
                "quote": {
                    "lastPrice": 175.50,
                    "bidPrice": 175.45,
                    "askPrice": 175.55,
                    "bidSize": 100,
                    "askSize": 200,
                    "totalVolume": 50000000,
                    "openPrice": 174.00,
                    "highPrice": 176.00,
                    "lowPrice": 173.50,
                    "closePrice": 174.50,
                    "netChange": 1.00,
                    "netPercentChange": 0.57,
                    "52WkHigh": 200.00,
                    "52WkLow": 125.00,
                    "marketCap": 3000000000000,
                    "peRatio": 25.5,
                    "divYield": 0.5,
                },
                "reference": {
                    "description": "Apple Inc",
                    "exchange": "Q",
                    "exchangeName": "NASDAQ",
                    "cusip": "037833100",
                },
            }
        }
    )


def schwab_quotes_payload() -> dict[str, Any]:
    """Return representative Schwab multi-quote data."""
    quotes = schwab_quote_payload()
    quotes["GOOGL"] = {
        "assetMainType": "EQUITY",
        "quote": {
            "lastPrice": 140.25,
            "netChange": -2.50,
            "netPercentChange": -1.75,
            "totalVolume": 25000000,
            "bidPrice": 140.20,
            "askPrice": 140.30,
        },
        "reference": {
            "description": "Alphabet Inc",
            "exchange": "Q",
            "exchangeName": "NASDAQ",
            "cusip": "02079K305",
        },
    }
    return quotes


def schwab_price_history_payload() -> dict[str, Any]:
    """Return representative Schwab price-history data."""
    return _copy(
        {
            "candles": [
                {
                    "open": 174.00,
                    "high": 175.00,
                    "low": 173.50,
                    "close": 174.50,
                    "volume": 1000000,
                    "datetime": 1672531200000,
                },
                {
                    "open": 174.50,
                    "high": 176.00,
                    "low": 174.00,
                    "close": 175.50,
                    "volume": 1500000,
                    "datetime": 1672534800000,
                },
            ],
            "empty": False,
        }
    )


def schwab_account_numbers_payload() -> list[dict[str, Any]]:
    """Return representative Schwab account-number hashes."""
    return _copy_list(
        [
            {"accountNumber": "12345678", "hashValue": "abc123def456"},
            {"accountNumber": "87654321", "hashValue": "xyz789uvw012"},
        ]
    )


def schwab_account_payload() -> dict[str, Any]:
    """Return representative Schwab account data with positions."""
    return _copy(
        {
            "securitiesAccount": {
                "accountNumber": "12345678",
                "type": "MARGIN",
                "roundTrips": 0,
                "isDayTrader": False,
                "isClosingOnlyRestricted": False,
                "positions": [
                    {
                        "shortQuantity": 0.0,
                        "averagePrice": 150.0,
                        "currentDayProfitLoss": 50.0,
                        "currentDayProfitLossPercentage": 2.5,
                        "longQuantity": 10.0,
                        "settledLongQuantity": 10.0,
                        "settledShortQuantity": 0.0,
                        "instrument": {
                            "assetType": "EQUITY",
                            "cusip": "037833100",
                            "symbol": "AAPL",
                        },
                        "marketValue": 1500.0,
                    }
                ],
            }
        }
    )


def schwab_accounts_payload() -> list[dict[str, Any]]:
    """Return representative Schwab accounts list data."""
    accounts = [schwab_account_payload()]
    second = schwab_account_payload()
    second["securitiesAccount"]["accountNumber"] = "87654321"
    second["securitiesAccount"]["type"] = "CASH"
    accounts.append(second)
    return accounts


def schwab_balances_payload() -> dict[str, Any]:
    """Return representative Schwab account balance data."""
    return _copy(
        {
            "securitiesAccount": {
                "accountNumber": "12345678",
                "type": "MARGIN",
                "currentBalances": {
                    "liquidationValue": 50000.0,
                    "cashBalance": 10000.0,
                    "buyingPower": 25000.0,
                    "availableFunds": 24000.0,
                    "longMarketValue": 40000.0,
                    "shortMarketValue": 0.0,
                },
                "initialBalances": {
                    "accountValue": 48000.0,
                    "cashBalance": 9500.0,
                },
            }
        }
    )


def broker_auth_error_payload() -> dict[str, Any]:
    """Return a structured broker authentication error response."""
    return _copy({"result": {"error": "Not authenticated", "status": "error"}})


def broker_api_error_payload() -> dict[str, Any]:
    """Return a structured broker API error response."""
    return _copy({"result": {"error": "API Error", "status": "error"}})
