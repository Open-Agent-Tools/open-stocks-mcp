# Tool Comparison: Robinhood vs Schwab

**Purpose**: Pairwise comparison of current Robinhood MCP tools to future Schwab MCP tools
**Current**: 81 Robinhood tools (80 active, 4 deprecated)
**Planned**: ~77 Schwab tools (70 common, 7 Schwab-specific)

---

## Legend

- ✅ **Direct Match** - Tool has 1:1 equivalent in Schwab API
- 🔄 **Partial Match** - Similar functionality but different API structure
- ⚠️ **Requires Mapping** - Schwab API requires different approach to achieve same result
- ❌ **Not Available** - No Schwab equivalent (Robinhood-specific feature)
- ➕ **Schwab Bonus** - Additional capability in Schwab not in Robinhood

---

## Account Management Tools (14 tools)

| Robinhood Tool | Schwab Status | Schwab Tool/Method | Notes |
|----------------|---------------|-------------------|-------|
| `get_account_info` | ✅ Direct Match | `schwab_get_account` | Maps to `client.get_account(hash_value)` |
| `get_account_details` | ✅ Direct Match | `schwab_get_account_details` | Schwab provides more detailed balance info |
| `get_portfolio` | ✅ Direct Match | `schwab_get_portfolio` | Calculated from account positions |
| `get_positions` | ✅ Direct Match | `schwab_get_positions` | Part of account response |
| `get_account_profile` | 🔄 Partial Match | `schwab_get_user_preferences` | Different structure but similar data |
| `get_account_settings` | 🔄 Partial Match | `schwab_get_user_preferences` | Combined in user preferences |
| `get_basic_profile` | 🔄 Partial Match | `schwab_get_user_preferences` | Subset of user preferences |
| `get_user_profile` | 🔄 Partial Match | `schwab_get_user_preferences` | Subset of user preferences |
| `get_investment_profile` | ⚠️ Requires Mapping | `schwab_get_account` | Derive from account data |
| `get_security_profile` | ⚠️ Requires Mapping | `schwab_get_account` | Derive from account data |
| `get_complete_profile` | ⚠️ Requires Mapping | `schwab_get_all_account_data` | Aggregate multiple API calls |
| `get_build_user_profile` | ⚠️ Requires Mapping | `schwab_build_user_profile` | Custom aggregation function |
| `get_account_features` | ❌ Not Available | N/A | Robinhood-specific feature flags |
| `get_account_numbers` | ➕ Schwab Bonus | `schwab_get_account_numbers` | Hash value mapping |

**Summary**: 14 Robinhood tools → 10 Schwab tools (4 consolidated, 1 RH-only, 1 Schwab bonus)

---

## Portfolio & Holdings Tools (5 tools)

| Robinhood Tool | Schwab Status | Schwab Tool/Method | Notes |
|----------------|---------------|-------------------|-------|
| `get_build_holdings` | ✅ Direct Match | `schwab_get_build_holdings` | Calculate from positions + quotes |
| `get_day_trades` | ⚠️ Requires Mapping | `schwab_get_day_trades` | Extract from transaction history |
| `get_aggregate_positions` | ✅ Direct Match | `schwab_get_aggregate_positions` | Sum across all accounts |
| `get_all_option_positions` | ✅ Direct Match | `schwab_get_all_option_positions` | Filter positions by type |
| `get_open_option_positions` | ✅ Direct Match | `schwab_get_open_option_positions` | Filter by open status |

**Summary**: 5 Robinhood tools → 5 Schwab tools (all mapped)

---

## Market Data Tools (20 tools)

| Robinhood Tool | Schwab Status | Schwab Tool/Method | Notes |
|----------------|---------------|-------------------|-------|
| `get_stock_price` | ✅ Direct Match | `schwab_get_stock_price` | `client.get_quote(symbol)` |
| `get_stock_quote_by_id` | 🔄 Partial Match | `schwab_get_stock_quote` | Schwab uses symbols, not IDs |
| `get_stock_info` | ✅ Direct Match | `schwab_get_instrument` | `client.get_instruments(symbol)` |
| `search_stocks` | ✅ Direct Match | `schwab_search_instruments` | `client.get_instruments(query)` |
| `find_instrument_data` | ✅ Direct Match | `schwab_get_instrument_by_cusip` | `client.get_instrument_by_cusip()` |
| `get_instruments_by_symbols` | ✅ Direct Match | `schwab_get_quotes` | `client.get_quotes(symbols)` |
| `get_price_history` | ✅ Direct Match | `schwab_get_price_history` | Multiple frequency options |
| `get_market_hours` | ✅ Direct Match | `schwab_get_market_hours` | `client.get_market_hours()` |
| `get_stock_earnings` | ❌ Not Available | N/A | Not in Schwab API (use 3rd party) |
| `get_stock_ratings` | ❌ Not Available | N/A | Not in Schwab API |
| `get_stock_news` | ❌ Not Available | N/A | Not in Schwab API |
| `get_stock_events` | ❌ Not Available | N/A | Not in Schwab API |
| `get_stock_splits` | ❌ Not Available | N/A | Not in Schwab API |
| `get_top_movers` | ✅ Direct Match | `schwab_get_movers` | `client.get_movers(index)` |
| `get_top_movers_sp500` | ✅ Direct Match | `schwab_get_movers_sp500` | `client.get_movers('$SPX')` |
| `get_top_100` | 🔄 Partial Match | `schwab_get_top_movers` | Use movers by index |
| `get_stocks_by_tag` | ❌ Not Available | N/A | Robinhood-specific tagging |
| `get_pricebook_by_symbol` | ➕ Schwab Bonus | `schwab_get_level2_data` | Schwab has better L2 data |
| `get_stock_level2_data` | ➕ Schwab Bonus | `schwab_stream_level2` | Real-time streaming available |
| `get_option_market_data` | ✅ Direct Match | `schwab_get_option_quote` | Part of option chain data |

**Summary**: 20 Robinhood tools → 14 Schwab tools (6 not available in Schwab, 2 Schwab bonuses)

**Missing in Schwab**: Earnings, ratings, news, events, splits require 3rd party data sources

---

## Options Tools (8 tools)

| Robinhood Tool | Schwab Status | Schwab Tool/Method | Notes |
|----------------|---------------|-------------------|-------|
| `get_options_chains` | ✅ Direct Match | `schwab_get_option_chain` | `client.get_option_chain(symbol)` |
| `find_tradable_options` | ✅ Direct Match | `schwab_find_tradable_options` | Filter option chain results |
| `get_option_historicals` | ❌ Not Available | N/A | Schwab doesn't provide historical options pricing |
| `get_open_option_positions_with_details` | ✅ Direct Match | `schwab_get_option_positions_detailed` | Enrich with market data |
| `get_option_market_data` | ✅ Direct Match | `schwab_get_option_quote` | From option chain |
| `get_options_orders` | ✅ Direct Match | `schwab_get_option_orders` | Filter orders by type |
| `get_all_open_option_orders` | ✅ Direct Match | `schwab_get_open_option_orders` | Filter by status |
| `get_aggregate_positions` | ✅ Direct Match | `schwab_get_aggregate_positions` | (Duplicate - see Portfolio) |

**Summary**: 8 Robinhood tools → 7 Schwab tools (1 not available)

**Missing in Schwab**: Historical options pricing data

---

## Trading Tools (15 active + 4 deprecated)

| Robinhood Tool | Schwab Status | Schwab Tool/Method | Notes |
|----------------|---------------|-------------------|-------|
| **Stock Orders** |
| `order_buy_market` | ✅ Direct Match | `schwab_order_buy_market` | `client.place_order()` with market type |
| `order_sell_market` | ✅ Direct Match | `schwab_order_sell_market` | `client.place_order()` with market type |
| `order_buy_limit` | ✅ Direct Match | `schwab_order_buy_limit` | `client.place_order()` with limit type |
| `order_sell_limit` | ✅ Direct Match | `schwab_order_sell_limit` | `client.place_order()` with limit type |
| `order_sell_stop_loss` | ✅ Direct Match | `schwab_order_sell_stop` | `client.place_order()` with stop type |
| ~~`order_buy_stop_loss`~~ | ❌ Deprecated | N/A | Deprecated in both |
| ~~`order_buy_trailing_stop`~~ | ❌ Deprecated | N/A | Deprecated in both |
| ~~`order_sell_trailing_stop`~~ | ❌ Deprecated | N/A | Deprecated in both |
| ~~`order_buy_fractional_by_price`~~ | ❌ Deprecated | N/A | Deprecated in both |
| **Option Orders** |
| `order_buy_option_limit` | ✅ Direct Match | `schwab_order_buy_option_limit` | Option order builder |
| `order_sell_option_limit` | ✅ Direct Match | `schwab_order_sell_option_limit` | Option order builder |
| `order_option_credit_spread` | ✅ Direct Match | `schwab_order_option_credit_spread` | Multi-leg option order |
| `order_option_debit_spread` | ✅ Direct Match | `schwab_order_option_debit_spread` | Multi-leg option order |
| **Order Management** |
| `get_stock_orders` | ✅ Direct Match | `schwab_get_stock_orders` | `client.get_orders_for_account()` |
| `get_all_open_stock_orders` | ✅ Direct Match | `schwab_get_open_stock_orders` | Filter by status |
| `cancel_stock_order` | ✅ Direct Match | `schwab_cancel_order` | `client.cancel_order()` |
| `cancel_all_stock_orders` | ✅ Direct Match | `schwab_cancel_all_stock_orders` | Iterate and cancel |
| `cancel_option_order` | ✅ Direct Match | `schwab_cancel_option_order` | `client.cancel_order()` |
| `cancel_all_option_orders` | ✅ Direct Match | `schwab_cancel_all_option_orders` | Iterate and cancel |
| | ➕ Schwab Bonus | `schwab_replace_order` | Modify existing orders |

**Summary**: 15 Robinhood active tools → 16 Schwab tools (1 bonus: replace_order)

**Schwab Advantage**: Can modify orders instead of cancel/recreate

---

## Dividend & Payment Tools (5 tools)

| Robinhood Tool | Schwab Status | Schwab Tool/Method | Notes |
|----------------|---------------|-------------------|-------|
| `get_dividends` | ⚠️ Requires Mapping | `schwab_get_dividends` | Extract from transactions |
| `get_dividends_by_instrument` | ⚠️ Requires Mapping | `schwab_get_dividends_by_symbol` | Filter transactions |
| `get_total_dividends` | ⚠️ Requires Mapping | `schwab_get_total_dividends` | Aggregate from transactions |
| `get_interest_payments` | ⚠️ Requires Mapping | `schwab_get_interest_payments` | Extract from transactions |
| `get_stock_loan_payments` | ⚠️ Requires Mapping | `schwab_get_stock_loan_payments` | Extract from transactions |

**Summary**: 5 Robinhood tools → 5 Schwab tools (all require transaction parsing)

**Implementation Note**: Schwab provides transactions, not pre-aggregated dividend data

---

## Watchlist Tools (5 tools)

| Robinhood Tool | Schwab Status | Schwab Tool/Method | Notes |
|----------------|---------------|-------------------|-------|
| `get_all_watchlists` | ❌ Not Available | N/A | Schwab API doesn't support watchlists |
| `get_watchlist_by_name` | ❌ Not Available | N/A | No watchlist API |
| `add_symbols_to_watchlist` | ❌ Not Available | N/A | No watchlist API |
| `remove_symbols_from_watchlist` | ❌ Not Available | N/A | No watchlist API |
| `get_watchlist_performance` | ❌ Not Available | N/A | No watchlist API |

**Summary**: 5 Robinhood tools → 0 Schwab tools

**Workaround**: Implement client-side watchlist storage (local file or database)

---

## Notifications & Alerts Tools (7 tools)

| Robinhood Tool | Schwab Status | Schwab Tool/Method | Notes |
|----------------|---------------|-------------------|-------|
| `get_notifications` | ❌ Not Available | N/A | Robinhood-specific |
| `get_latest_notification` | ❌ Not Available | N/A | Robinhood-specific |
| `get_margin_calls` | ⚠️ Requires Mapping | `schwab_check_margin_status` | Derive from account data |
| `get_margin_interest` | ⚠️ Requires Mapping | `schwab_get_margin_interest` | Extract from transactions |
| `get_referrals` | ❌ Not Available | N/A | Robinhood-specific |
| `get_subscription_fees` | ❌ Not Available | N/A | Robinhood Gold specific |
| `get_account_features` | ❌ Not Available | N/A | Robinhood-specific |

**Summary**: 7 Robinhood tools → 2 Schwab tools (5 not applicable)

**Missing in Schwab**: Push notifications, referral program, subscription features

---

## Cryptocurrency Tools (3 tools)

| Robinhood Tool | Schwab Status | Schwab Tool/Method | Notes |
|----------------|---------------|-------------------|-------|
| `get_crypto_positions` | ❌ Not Available | N/A | Schwab doesn't support crypto |
| `get_crypto_quote` | ❌ Not Available | N/A | No crypto trading |
| `order_buy_crypto` | ❌ Not Available | N/A | No crypto trading |

**Summary**: 3 Robinhood tools → 0 Schwab tools

**Note**: Schwab does not offer cryptocurrency trading

---

## Transaction History Tools (New in Schwab)

| Robinhood Tool | Schwab Status | Schwab Tool/Method | Notes |
|----------------|---------------|-------------------|-------|
| N/A | ➕ Schwab Bonus | `schwab_get_transaction` | `client.get_transaction()` |
| N/A | ➕ Schwab Bonus | `schwab_get_transactions` | `client.get_transactions()` with filters |
| N/A | ➕ Schwab Bonus | `schwab_get_transactions_by_date` | Date range filtering |

**Summary**: 0 Robinhood tools → 3 Schwab tools

**Schwab Advantage**: Comprehensive transaction history API

---

## Streaming Tools (New in Schwab)

| Robinhood Tool | Schwab Status | Schwab Tool/Method | Notes |
|----------------|---------------|-------------------|-------|
| `get_stock_level2_data` | 🔄 Partial Match | `schwab_stream_quotes` | Real-time streaming |
| `get_pricebook_by_symbol` | 🔄 Partial Match | `schwab_stream_level2` | Real-time order book |
| N/A | ➕ Schwab Bonus | `schwab_stream_option_quotes` | Real-time option pricing |
| N/A | ➕ Schwab Bonus | `schwab_stream_account_activity` | Real-time account updates |

**Summary**: 2 Robinhood tools → 4 Schwab streaming tools

**Schwab Advantage**: Native streaming support via WebSockets

---

## Utility Tools (1 tool)

| Robinhood Tool | Schwab Status | Schwab Tool/Method | Notes |
|----------------|---------------|-------------------|-------|
| `list_available_tools` | ✅ Direct Match | `schwab_list_available_tools` | MCP meta-tool |

**Summary**: 1 Robinhood tool → 1 Schwab tool

---

## Summary Statistics

### Tool Count by Category

| Category | Robinhood Tools | Schwab Tools | Status |
|----------|----------------|--------------|--------|
| Account Management | 14 | 10 | ⚠️ 4 consolidated, 1 RH-only |
| Portfolio & Holdings | 5 | 5 | ✅ All mapped |
| Market Data | 20 | 14 | ⚠️ 6 missing (earnings, news, etc.) |
| Options | 8 | 7 | ⚠️ 1 missing (historical pricing) |
| Trading | 15 | 16 | ✅ + 1 bonus (replace_order) |
| Dividends & Payments | 5 | 5 | ⚠️ All require transaction parsing |
| Watchlists | 5 | 0 | ❌ Not in Schwab API |
| Notifications | 7 | 2 | ❌ 5 RH-specific features |
| Cryptocurrency | 3 | 0 | ❌ Schwab doesn't support crypto |
| Transactions | 0 | 3 | ➕ Schwab bonus feature |
| Streaming | 2 | 4 | ➕ Schwab bonus feature |
| Utilities | 1 | 1 | ✅ Meta-tool |
| **TOTAL** | **85** | **67** | **79% coverage** |

### Mapping Status

| Status | Count | Percentage | Description |
|--------|-------|------------|-------------|
| ✅ Direct Match | 45 | 53% | 1:1 API equivalent exists |
| 🔄 Partial Match | 8 | 9% | Similar functionality, different structure |
| ⚠️ Requires Mapping | 10 | 12% | Achievable but needs custom logic |
| ❌ Not Available | 22 | 26% | No Schwab equivalent |
| ➕ Schwab Bonus | 9 | +11% | New capabilities in Schwab |

### Coverage Analysis

**High Coverage Areas (90-100%)**:
- Portfolio & Holdings (100%)
- Trading (107% - includes bonus)
- Options (88%)
- Account Management (71%)

**Medium Coverage Areas (50-89%)**:
- Market Data (70%)
- Dividends (100% but requires mapping)

**Low Coverage Areas (0-49%)**:
- Notifications (29%)
- Watchlists (0%)
- Cryptocurrency (0%)

### Robinhood-Only Features (22 tools, 26%)

**Cannot be ported to Schwab**:
1. All crypto tools (3)
2. Most notification tools (5)
3. All watchlist tools (5)
4. Earnings/news/ratings data (6)
5. RH-specific features (3): referrals, subscriptions, account features

### Schwab-Only Features (9 bonus tools, +11%)

**New capabilities**:
1. Transaction history API (3 tools)
2. Streaming quotes (4 tools)
3. Order replacement (1 tool)
4. Account number hashing (1 tool)

---

## Implementation Priority

### Phase 1: Core Trading (80% user value)

**High Priority - Essential for trading**:
- Account management (10 tools)
- Portfolio & holdings (5 tools)
- Basic market data (10 tools)
- Trading operations (16 tools)
- Order management (4 tools)

**Total**: 45 tools, ~80% of typical user needs

### Phase 2: Enhanced Data (15% user value)

**Medium Priority - Nice to have**:
- Options (7 tools)
- Dividends (5 tools, requires transaction parsing)
- Advanced market data (4 tools)

**Total**: 16 tools, additional 15% value

### Phase 3: Advanced Features (5% user value)

**Low Priority - Power users**:
- Transaction history (3 tools)
- Streaming (4 tools)
- Custom aggregations (varies)

**Total**: 7+ tools, final 5% value

---

## Migration Recommendations

### For Users Migrating from Robinhood to Schwab

**Full Compatibility** (no change needed):
- Account queries
- Portfolio tracking
- Stock/option trading
- Basic market data

**Workarounds Required**:
- **Watchlists**: Use local file storage or separate watchlist service
- **News/Earnings**: Integrate 3rd party API (Alpha Vantage, Finnhub, etc.)
- **Historical Options**: Not available, use alternative data source
- **Crypto**: Use separate crypto exchange

**Features Lost**:
- Robinhood notifications
- Referral tracking
- Subscription fee tracking
- Robinhood Gold features

**Features Gained**:
- Real-time streaming quotes
- Transaction history API
- Order modification (replace)
- Better institutional data quality

### For Users Using Both Brokers

**Recommended Approach**:
- Use Robinhood for: Crypto, watchlists, news aggregation
- Use Schwab for: Serious trading, better data quality, streaming
- Use MCP tools with broker prefix: `robinhood_*` vs `schwab_*`

---

## Technical Implementation Notes

### API Response Normalization

**Challenge**: Schwab and Robinhood return different JSON structures

**Example - Portfolio Data**:

```python
# Robinhood response
{
    "market_value": "10000.00",
    "total_return_today": "250.50",
    "total_return_today_percent": "2.51"
}

# Schwab response (normalized to match)
{
    "securitiesAccount": {
        "currentBalances": {
            "liquidationValue": 10000.00,
            "cashBalance": 5000.00
        }
    }
}

# Our normalized output (common format)
{
    "result": {
        "market_value": 10000.00,
        "total_return_today": 250.50,
        "cash_balance": 5000.00
    }
}
```

**Solution**: Create normalization layer in broker adapters

### OAuth vs Session Management

**Robinhood**: Username/password with pickle file
**Schwab**: OAuth 2.0 with token refresh

**Impact on Tools**: None - abstracted in broker layer

### Rate Limiting Differences

| Broker | Rate Limit | Implementation |
|--------|------------|----------------|
| Robinhood | ~30 req/min | Token bucket in code |
| Schwab | ~120 req/min | Token bucket in code |

**Solution**: Per-broker rate limiters

---

## Open Questions

1. **Watchlist Replacement**: Should we build a persistent watchlist storage layer?
   - **Option A**: SQLite database for MCP server
   - **Option B**: JSON file storage
   - **Option C**: Let users manage externally

2. **Missing Data Sources**: Should we integrate 3rd party APIs for news/earnings?
   - **Option A**: Add as separate tools (e.g., `alpha_vantage_get_earnings`)
   - **Option B**: Transparent fallback from Schwab tools
   - **Option C**: Document as limitation

3. **Streaming Architecture**: How to expose Schwab streaming in MCP?
   - **Option A**: Use SSE endpoint for streaming quotes
   - **Option B**: Polling with cached data
   - **Option C**: WebSocket support (Phase 6+)

---

## Conclusion

**Overall Coverage**: 79% of Robinhood tools have Schwab equivalents

**Recommended Approach**:
1. Implement Phase 1 (45 core tools) first
2. Add Phase 2 (16 enhanced tools) for completeness
3. Consider Phase 3 (7+ advanced tools) based on user demand
4. Document limitations clearly (no crypto, no watchlists)
5. Highlight Schwab advantages (streaming, transactions)

**Total Implementation**: 67 Schwab tools matching 67 Robinhood tools (79% coverage)

**Schwab Bonuses**: +9 new tools (transactions, streaming, order modification)

**Final Tool Count**:
- Robinhood: 80 active tools (85 total with deprecated)
- Schwab: 67 tools (79% coverage) + 9 bonus = 76 total tools

This creates a robust multi-broker MCP server with broad functionality across both platforms.
