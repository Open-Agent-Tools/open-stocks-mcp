"""Schema checks for shared broker API fixture payloads."""

from typing import Any

from tests.fixtures import broker_payloads


def test_robinhood_quote_payload_contains_stock_price_fields() -> None:
    payload = broker_payloads.robinhood_quote_payload()

    assert {
        "previous_close",
        "volume",
        "ask_price",
        "bid_price",
        "last_trade_price",
    }.issubset(payload)


def test_robinhood_account_payloads_contain_consumed_fields() -> None:
    profile = broker_payloads.robinhood_user_profile_payload()
    portfolio = broker_payloads.robinhood_portfolio_payload()
    positions = broker_payloads.robinhood_positions_payload()
    phoenix = broker_payloads.robinhood_phoenix_account_payload()
    holdings = broker_payloads.robinhood_build_holdings_payload()

    assert {"username", "created_at"}.issubset(profile)
    assert {"market_value", "equity", "buying_power"}.issubset(portfolio)
    assert {"instrument", "quantity", "average_buy_price", "updated_at"}.issubset(
        positions[0]
    )
    assert "results" in phoenix
    assert {"portfolio_equity", "total_equity", "account_buying_power"}.issubset(
        phoenix["results"][0]
    )
    assert {"price", "quantity", "equity", "type", "name"}.issubset(
        holdings["AAPL"]
    )


def test_schwab_market_payloads_contain_consumed_fields() -> None:
    quote = broker_payloads.schwab_quote_payload()
    price_history = broker_payloads.schwab_price_history_payload()

    quote_fields = quote["AAPL"]["quote"]
    assert {
        "lastPrice",
        "bidPrice",
        "askPrice",
        "totalVolume",
        "openPrice",
        "highPrice",
        "lowPrice",
        "closePrice",
        "netChange",
        "netPercentChange",
    }.issubset(quote_fields)
    assert {"assetMainType", "reference"}.issubset(quote["AAPL"])
    assert {"description", "exchange", "exchangeName", "cusip"}.issubset(
        quote["AAPL"]["reference"]
    )
    assert "candles" in price_history
    assert {"open", "high", "low", "close", "volume", "datetime"}.issubset(
        price_history["candles"][0]
    )


def test_schwab_account_payloads_contain_consumed_fields() -> None:
    numbers = broker_payloads.schwab_account_numbers_payload()
    account = broker_payloads.schwab_account_payload()
    balances = broker_payloads.schwab_balances_payload()

    assert {"accountNumber", "hashValue"}.issubset(numbers[0])
    securities_account: dict[str, Any] = account["securitiesAccount"]
    assert {"accountNumber", "type", "positions"}.issubset(securities_account)
    assert {
        "instrument",
        "longQuantity",
        "shortQuantity",
        "averagePrice",
        "marketValue",
    }.issubset(securities_account["positions"][0])
    assert {"currentBalances", "initialBalances"}.issubset(
        balances["securitiesAccount"]
    )


def test_broker_error_payloads_are_structured_and_copy_safe() -> None:
    first_error = broker_payloads.broker_auth_error_payload()
    second_error = broker_payloads.broker_auth_error_payload()
    first_quote = broker_payloads.robinhood_quote_payload()
    second_quote = broker_payloads.robinhood_quote_payload()

    assert first_error["result"]["status"] == "error"
    assert "error" in first_error["result"]

    first_error["result"]["status"] = "mutated"
    first_quote["symbol"] = "MSFT"

    assert second_error["result"]["status"] == "error"
    assert second_quote["symbol"] == "AAPL"
