# Open Stocks MCP — Tool Reference

Total tools: 150

## account_details

Gets comprehensive account details including buying power and cash balances.

## account_features

Gets comprehensive account features and settings.

## account_info

Gets basic Robinhood account information.

## account_profile

Gets trading account profile and configuration.

## account_settings

Gets account settings and preferences.

## add_to_watchlist

Adds symbols to a watchlist.

    Args:
        watchlist_name: Name of the watchlist
        symbols: List of stock symbols to add


## aggregate_option_positions

Gets aggregated option positions collapsed by underlying stock.

## aggregated_portfolio

Get a unified portfolio view aggregated across all registered brokers.

    Combines positions and summary values from Robinhood and Schwab into a single
    normalized response. Brokers that are not authenticated contribute a degraded
    (status=unavailable) entry so partial information is always returned.

    Returns:
        Dict with aggregated totals, per-broker rollups, positions list,
        partial_failure flag, and unavailable_brokers list.


## all_option_positions

Gets all option positions ever held.

## all_watchlists

Gets all user-created watchlists.

## basic_profile

Gets basic user profile information.

## broker_comparison

Get side-by-side broker comparison for pricing, holdings, and orders.

    Args:
        symbols: Optional list of symbols to filter by.
        include_orders: Whether to include recent orders.
        max_orders: Maximum number of orders to return per broker.


## broker_status

Gets authentication status for all configured brokers.

    Returns information about which brokers are available, authenticated,
    or experiencing issues. Use this to troubleshoot authentication problems.

    Returns:
        Dictionary with broker authentication status for each broker


## build_holdings

Builds comprehensive holdings with dividend information and performance metrics.

    Returns detailed holdings data including cost basis, equity, dividends, and performance.


## build_user_profile

Builds comprehensive user profile with equity, cash, and dividend totals.

    Returns complete financial profile including total equity, cash balances, and dividend totals.


## buy_option_limit

Places a limit buy order for an option.

    Args:
        instrument_id: The option instrument ID
        quantity: The number of option contracts to buy
        limit_price: The maximum price per contract


## buy_stock_limit

Places a limit buy order for a stock.

    Args:
        symbol: The stock symbol to buy (e.g., "AAPL")
        quantity: The number of shares to buy
        limit_price: The maximum price per share


## buy_stock_market

Places a market buy order for a stock.

    Args:
        symbol: The stock symbol to buy (e.g., "AAPL")
        quantity: The number of shares to buy


## cancel_all_option_orders_tool

Cancels all open option orders.

## cancel_all_stock_orders_tool

Cancels all open stock orders.

## cancel_option_order_by_id

Cancels a specific option order.

    Args:
        order_id: The ID of the order to cancel


## cancel_stock_order_by_id

Cancels a specific stock order.

    Args:
        order_id: The ID of the order to cancel


## complete_profile

Gets complete user profile combining all profile types.

## day_trades

Gets pattern day trading information and tracking.

    Returns day trade count, remaining day trades, PDT status, and buying power information.


## dividends

Gets all dividend payment history for the account.

## dividends_by_instrument

Gets dividend history for a specific stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")


## find_instruments

Searches for instrument information by various criteria.

    Args:
        query: Search query string (can be symbol, company name, or other criteria)


## find_options

Finds tradable options with optional filtering.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
        expiration_date: Optional expiration date in YYYY-MM-DD format
        option_type: Optional option type ("call" or "put")


## health_check

Gets health status of the MCP server.

## instruments_by_symbols

Gets detailed instrument metadata for multiple symbols.

    Args:
        symbols: List of stock ticker symbols (e.g., ["AAPL", "GOOGL", "MSFT"])


## interest_payments

Gets interest payment history from cash management.

## investment_profile

Gets investment profile and risk assessment.

## latest_notification

Gets the most recent notification.

## list_brokers

Lists all registered brokers and their availability.

    Returns:
        List of broker names and their authentication status


## list_tools

Provides a list of available tools and their descriptions.

## margin_calls

Gets margin call information.

## margin_interest

Gets margin interest charges and rates.

## market_hours

Gets current market hours and status.

## metrics_summary

Gets comprehensive metrics summary for monitoring.

## notifications

Gets account notifications and alerts.

    Args:
        count: Number of notifications to retrieve (default: 20)


## open_option_orders

Retrieves all open option orders.

## open_option_positions

Gets currently open option positions.

## open_option_positions_with_details

Gets currently open option positions with enriched details including call/put type.

    This enhanced version includes complete option instrument details for each position:
    - option_type: "call" or "put"
    - strike_price: Strike price of the option
    - option_symbol: OCC option symbol
    - tradability: Trading status
    - state: Option state (active, expired, etc.)
    - underlying_symbol: Underlying stock symbol
    - enrichment_success_rate: Percentage of positions successfully enriched

    Use this instead of open_option_positions() when you need complete option details.


## open_stock_orders

Retrieves all open stock orders.

## option_credit_spread

Places a credit spread order (sell short option, buy long option).

    Args:
        short_instrument_id: The option instrument ID to sell (short leg)
        long_instrument_id: The option instrument ID to buy (long leg)
        quantity: The number of spread contracts
        credit_price: The net credit received per spread


## option_debit_spread

Places a debit spread order (buy long option, sell short option).

    Args:
        short_instrument_id: The option instrument ID to sell (short leg)
        long_instrument_id: The option instrument ID to buy (long leg)
        quantity: The number of spread contracts
        debit_price: The net debit paid per spread


## option_historicals

Gets historical price data for an option contract.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
        expiration_date: Expiration date in YYYY-MM-DD format
        strike_price: Strike price as string
        option_type: Option type ("call" or "put")
        interval: Time interval (default: "hour")
        span: Time span (default: "week")


## option_market_data

Gets market data for a specific option contract.

    Args:
        option_id: Unique option contract ID


## options_chains

Gets complete option chains for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")


## options_orders

Retrieves a list of recent options order history and their statuses.

## portfolio

Provides a high-level overview of the portfolio.

## positions

Gets current stock positions with quantities and values.

## price_history

Gets historical price data for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
        period: Time period ("day", "week", "month", "3month", "year", "5year")


## pricebook_by_symbol

Gets Level II order book data for a symbol (requires Gold subscription).

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")


## rate_limit_status

Gets current rate limit usage and statistics.

## referrals

Gets referral program information.

## remove_from_watchlist

Removes symbols from a watchlist.

    Args:
        watchlist_name: Name of the watchlist
        symbols: List of stock symbols to remove


## schwab_account

Get Schwab account details including balances and positions.

    Args:
        account_hash: Account hash from schwab_account_numbers
        include_positions: Whether to include positions (default: True)


## schwab_account_balances

Get account balances for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers


## schwab_account_numbers

Get Schwab account numbers and their hashes.

## schwab_accounts

Get all Schwab linked accounts with balances and positions.

    Args:
        include_positions: Whether to include positions (default: True)


## schwab_build_user_profile

Build a normalized Schwab user profile from account and preference data.

    Returns a complete financial profile including total equity, cash balances,
    and position counts across all accounts.


## schwab_buy_stock_limit

Place a limit buy order for stock.

    Args:
        account_hash: Account hash from schwab_account_numbers
        symbol: Stock ticker symbol
        quantity: Number of shares to buy
        price: Limit price


## schwab_buy_stock_market

Place a market buy order for stock.

    Args:
        account_hash: Account hash from schwab_account_numbers
        symbol: Stock ticker symbol
        quantity: Number of shares to buy


## schwab_cancel_all_option_orders

Cancel all open option orders for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        max_results: Maximum orders to fetch before filtering


## schwab_cancel_all_stock_orders

Cancel all open equity orders for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        max_results: Maximum orders to fetch before filtering


## schwab_cancel_option_order

Cancel a specific option order.

    Args:
        account_hash: Account hash from schwab_account_numbers
        order_id: Option order ID to cancel


## schwab_cancel_order

Cancel a specific Schwab order.

    Args:
        account_hash: Account hash from schwab_account_numbers
        order_id: Order ID to cancel


## schwab_check_margin_status

Derive margin-call status from Schwab account balances.

## schwab_find_tradable_options

Find tradable option contracts filtered by expiration, type, and strike.

    Args:
        symbol: Stock ticker symbol
        expiration_date: Filter to contracts expiring on this date (YYYY-MM-DD)
        option_type: 'call' or 'put'
        strike: Strike price to filter on


## schwab_get_aggregate_positions

Aggregate Schwab positions across all linked accounts.

## schwab_get_all_account_data

Get a complete snapshot of all Schwab accounts and user preferences.

    Aggregates user preferences, account numbers, and all account data with positions.


## schwab_get_all_option_positions

Get all Schwab option positions across linked accounts.

## schwab_get_build_holdings

Build enriched holdings from Schwab positions and quotes.

## schwab_get_day_trades

Get day-trade counts derived from Schwab transaction history.

## schwab_get_dividends

Get dividend payments for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)


## schwab_get_dividends_by_symbol

Get dividend payments for a specific symbol in a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        symbol: Stock symbol to filter dividends by (case-insensitive)
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)


## schwab_get_instrument_by_cusip

Get instrument details by CUSIP identifier.

    Args:
        cusip: CUSIP identifier (leading zeros are preserved, e.g. '037833100')


## schwab_get_interest_payments

Get interest payments for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)


## schwab_get_margin_interest

Get Schwab margin-interest charges from transaction history.

## schwab_get_market_hours

Get market hours for a given market and optional date.

    Args:
        market: Market type ('equity', 'option', 'bond', 'forex', 'future')
        date: Optional ISO date string (e.g. '2026-05-20'). Defaults to today.


## schwab_get_movers

Get market movers for a given index.

    Args:
        index: Index to query (e.g. '$DJI', '$SPX', 'NASDAQ', 'NYSE', '$COMPX',
               'EQUITY_ALL', 'INDEX_ALL', 'OPTION_ALL', 'OPTION_CALL', 'OPTION_PUT',
               'OTCBB')
        sort_order: Optional sort order ('PERCENT_CHANGE_UP', 'PERCENT_CHANGE_DOWN',
                    'VOLUME', 'TRADES')
        frequency: Optional frequency in minutes (0, 1, 5, 10, 30, 60)


## schwab_get_movers_sp500

Get market movers for the S&P 500 index ($SPX).

    Args:
        sort_order: Optional sort order ('PERCENT_CHANGE_UP', 'PERCENT_CHANGE_DOWN',
                    'VOLUME', 'TRADES')
        frequency: Optional frequency in minutes (0, 1, 5, 10, 30, 60)


## schwab_get_open_option_positions

Get open Schwab option positions with non-zero net quantity.

## schwab_get_open_stock_orders

Get open (cancellable) equity orders for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        max_results: Maximum orders to fetch from API before filtering


## schwab_get_order

Get details for a specific Schwab order.

    Args:
        account_hash: Account hash from schwab_account_numbers
        order_id: Order ID to retrieve


## schwab_get_stock_loan_payments

Get stock loan (securities lending) payments for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)


## schwab_get_total_dividends

Get aggregate dividend totals with year grouping for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        start_date: Optional start date (YYYY-MM-DD). Schwab enforces a 60-day
            default lookback; pass an explicit start_date for older history.
        end_date: Optional end date (YYYY-MM-DD)


## schwab_get_transaction

Get details for a specific Schwab transaction.

    Args:
        account_hash: Account hash from schwab_account_numbers
        transaction_id: Transaction ID to retrieve


## schwab_get_user_preferences

Get Schwab user preferences including account list and streamer info.

    Consolidates account profile, settings, and user profile data.


## schwab_instrument

Get instrument information for a symbol.

    Args:
        symbol: Stock ticker symbol


## schwab_open_option_orders

Get open option orders for a Schwab account.

    Returns only orders with at least one option leg and a working/open status
    (WORKING, PENDING_ACTIVATION, QUEUED, ACCEPTED, AWAITING_CONDITION,
    AWAITING_MANUAL_REVIEW, AWAITING_PARENT_ORDER).

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        max_results: Maximum orders to fetch before filtering (default 50)


## schwab_option_buy_to_open

Buy an option to open a position (Schwab).

## schwab_option_chain

Get option chain for a symbol.

    Args:
        symbol: Stock ticker symbol
        contract_type: Type of contracts ('CALL', 'PUT', 'ALL')
        strike_count: Number of strikes above/below at-the-money price
        include_underlying_quote: Whether to include underlying quote


## schwab_option_chain_by_expiration

Get option chain filtered by expiration dates.

    Args:
        symbol: Stock ticker symbol
        from_date: Only return expirations after this date (YYYY-MM-DD)
        to_date: Only return expirations before this date (YYYY-MM-DD)
        contract_type: Type of contracts ('CALL', 'PUT', 'ALL')


## schwab_option_expirations

Get option expiration dates for a symbol.

    Args:
        symbol: Stock ticker symbol


## schwab_option_sell_to_close

Sell an option to close a position (Schwab).

## schwab_options_positions

Get current options positions for an account.

    Args:
        account_hash: Account hash from schwab_account_numbers


## schwab_order_buy_option_limit

Place a limit buy-to-open order for an option contract.

    Args:
        account_hash: Account hash from schwab_account_numbers
        option_symbol: OCC option symbol (e.g. "AAPL  251219C00150000")
        quantity: Number of contracts to buy
        price: Limit price as a string (e.g. "5.50")


## schwab_order_option_credit_spread

Place a vertical credit spread option order.

    For CALL: bear call spread. For PUT: bull put spread.

    Args:
        account_hash: Account hash from schwab_account_numbers
        option_type: "CALL" or "PUT"
        short_symbol: OCC symbol for the leg you sell (collects premium)
        long_symbol: OCC symbol for the hedge/protective leg
        quantity: Number of spread contracts
        net_credit: Net credit received as a string (e.g. "2.00")


## schwab_order_option_debit_spread

Place a vertical debit spread option order.

    For CALL: bull call spread. For PUT: bear put spread.

    Args:
        account_hash: Account hash from schwab_account_numbers
        option_type: "CALL" or "PUT"
        long_symbol: OCC symbol for the leg you buy (main directional position)
        short_symbol: OCC symbol for the hedge/short leg
        quantity: Number of spread contracts
        net_debit: Net debit paid as a string (e.g. "3.00")


## schwab_order_sell_option_limit

Place a limit sell-to-close order for an option contract.

    Args:
        account_hash: Account hash from schwab_account_numbers
        option_symbol: OCC option symbol (e.g. "AAPL  251219C00150000")
        quantity: Number of contracts to sell
        price: Limit price as a string (e.g. "4.00")


## schwab_order_sell_stop

Place a stop sell order for stock.

    Args:
        account_hash: Account hash from schwab_account_numbers
        symbol: Stock ticker symbol
        quantity: Number of shares to sell
        stop_price: Stop trigger price as a string (e.g. "148.00")


## schwab_orders

Get orders for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        max_results: Maximum number of orders to return (default: 50)


## schwab_place_order

Place a generic Schwab order using a raw order specification.

    Args:
        account_hash: Account hash from schwab_account_numbers
        order_spec: Order specification dict as accepted by the Schwab API
            (typically produced via schwab order builder helpers)


## schwab_portfolio

Get Schwab portfolio positions for a specific account.

    Args:
        account_hash: Account hash from schwab_account_numbers


## schwab_price_history

Get price history for a stock symbol.

    Args:
        symbol: Stock ticker symbol
        period_type: Type of period ('day', 'month', 'year', 'ytd')
        period: Number of periods
        frequency_type: Frequency type ('minute', 'daily', 'weekly', 'monthly')
        frequency: Frequency value


## schwab_quote

Get current quote for a stock symbol from Schwab.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')


## schwab_quotes

Get current quotes for multiple stock symbols from Schwab.

    Args:
        symbols: List of stock ticker symbols


## schwab_replace_order

Replace (modify) an existing Schwab order.

    Args:
        account_hash: Account hash from schwab_account_numbers
        order_id: ID of the order to replace
        order_spec: New order specification dict (use order builder helpers)


## schwab_search_instruments

Search for instruments by symbol or name.

    Args:
        query: Symbol or company name to search


## schwab_sell_stock_limit

Place a limit sell order for stock.

    Args:
        account_hash: Account hash from schwab_account_numbers
        symbol: Stock ticker symbol
        quantity: Number of shares to sell
        price: Limit price


## schwab_sell_stock_market

Place a market sell order for stock.

    Args:
        account_hash: Account hash from schwab_account_numbers
        symbol: Stock ticker symbol
        quantity: Number of shares to sell


## schwab_stream_account_activity

Get latest account activity events from Schwab streaming.

## schwab_stream_level2

Get a Level 2 snapshot from Schwab streaming cache for a symbol.

## schwab_stream_option_quotes

Get real-time option quote snapshots from Schwab streaming.

    Args:
        symbols: List of Schwab option symbols (e.g. ['AAPL  260619C00150000'])


## schwab_stream_quotes

Get real-time equity quote snapshots from Schwab streaming.

    Args:
        symbols: List of equity ticker symbols.


## schwab_transactions

Get Schwab transactions with optional date/type/symbol filters.

## schwab_transactions_by_date

Get Schwab transactions constrained by required start and end dates.

## search_stocks_tool

Searches for stocks by symbol or company name.

    Args:
        query: Search query (symbol or company name)


## security_profile

Gets security profile and settings.

## sell_option_limit

Places a limit sell order for an option.

    Args:
        instrument_id: The option instrument ID
        quantity: The number of option contracts to sell
        limit_price: The minimum price per contract


## sell_stock_limit

Places a limit sell order for a stock.

    Args:
        symbol: The stock symbol to sell (e.g., "AAPL")
        quantity: The number of shares to sell
        limit_price: The minimum price per share


## sell_stock_market

Places a market sell order for a stock.

    Args:
        symbol: The stock symbol to sell (e.g., "AAPL")
        quantity: The number of shares to sell


## sell_stock_stop_loss

Places a stop loss sell order for a stock.

    Args:
        symbol: The stock symbol to sell (e.g., "AAPL")
        quantity: The number of shares to sell
        stop_price: The stop price that triggers the order


## session_status

Gets current session status and authentication information.

## stock_earnings

Gets earnings reports for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")


## stock_events

Gets corporate events for a stock (for owned positions).

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")


## stock_info

Gets detailed company information and fundamentals.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")


## stock_level2_data

Gets Level II market data for a stock (Gold subscription required).

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")


## stock_loan_payments

Gets stock loan payment history from the stock lending program.

## stock_news

Gets news stories for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")


## stock_orders

Retrieves a list of recent stock order history and their statuses.

## stock_price

Gets current stock price and basic metrics.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")


## stock_quote_by_id

Gets stock quote using Robinhood's internal instrument ID.

    Args:
        instrument_id: Robinhood's internal instrument ID


## stock_ratings

Gets analyst ratings for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")


## stock_splits

Gets stock split history for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")


## stocks_by_tag

Gets stocks filtered by market category tag.

    Args:
        tag: Market category tag (e.g., 'technology', 'biopharmaceutical', 'upcoming-earnings')


## subscription_fees

Gets Robinhood Gold subscription fees.

## top_100_stocks

Gets top 100 most popular stocks on Robinhood.

## top_movers

Gets top 20 movers on Robinhood.

## top_movers_sp500

Gets top S&P 500 movers for the day.

    Args:
        direction: Direction of movement, either 'up' or 'down' (default: 'up')


## total_dividends

Gets total dividends received across all time.

## unified_add_to_watchlist

Adds symbols to a watchlist across supported brokers.

    Args:
        watchlist_name: Name of the watchlist
        symbols: List of stock symbols to add
        brokers: Optional list of broker names to target


## unified_remove_from_watchlist

Removes symbols from a watchlist across supported brokers.

    Args:
        watchlist_name: Name of the watchlist
        symbols: List of stock symbols to remove
        brokers: Optional list of broker names to target


## unified_watchlist_by_name

Gets a specific watchlist by name across supported brokers.

    Args:
        watchlist_name: Name of the watchlist
        brokers: Optional list of broker names to include


## unified_watchlists

Gets all watchlists aggregated across supported brokers.

    Args:
        brokers: Optional list of broker names to include (e.g., ["robinhood", "schwab"])


## user_profile

Gets comprehensive user profile information.

## watchlist_by_name

Gets contents of a specific watchlist by name.

    Args:
        watchlist_name: Name of the watchlist to retrieve


## watchlist_performance

Gets performance metrics for a watchlist.

    Args:
        watchlist_name: Name of the watchlist to analyze
