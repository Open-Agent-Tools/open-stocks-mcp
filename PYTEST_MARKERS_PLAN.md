# Pytest Markers Implementation Plan for Open Stocks MCP

## 📋 Analysis of open-paper-trading-mcp Approach

### Current Success Pattern from open-paper-trading-mcp:
- **User Journey Markers**: 10 journey-based markers for logical test grouping
- **Technical Markers**: unit, integration, performance, slow, database, live_data, robinhood
- **Targeted Testing**: Run specific user journeys to avoid timeouts and focus testing effort
- **Benefits**: Faster feedback loops, better test organization, reduced timeout issues

## 🎯 Proposed Pytest Markers for Open Stocks MCP

### A. Core Technical Markers (already partially implemented)
```python
# Basic test types
"unit: Unit tests - isolated component testing"
"integration: Integration tests - may require credentials/authentication" 
"slow: Slow running tests - can be skipped for fast feedback"
"live_market: Tests requiring live market data/API calls"
"robinhood: Tests using live Robinhood API calls"
"exception_test: Exception handling and error state tests"
"agent_evaluation: ADK agent evaluation tests"

# Performance and environment
"performance: Performance and load testing"
"auth_required: Tests requiring Robinhood authentication"
"rate_limited: Tests that may hit API rate limits"
```

### B. User Journey Markers (NEW - based on MCP tool categories)

#### 1. **Account Management Journey**
```python
"journey_account: Account information, settings, and profile management tests"
# Tools: account_info, account_details, account_profile, basic_profile, 
#        complete_profile, investment_profile, security_profile, account_settings
```

#### 2. **Portfolio & Holdings Journey** 
```python
"journey_portfolio: Portfolio overview, positions, and holdings analysis tests"
# Tools: portfolio, positions, build_holdings, build_user_profile, day_trades
```

#### 3. **Market Data Journey**
```python
"journey_market_data: Stock quotes, market info, and research data tests"
# Tools: stock_price, stock_info, market_hours, price_history, search_stocks_tool,
#        find_instruments, instruments_by_symbols, stock_quote_by_id
```

#### 4. **Trading & Orders Journey**
```python
"journey_trading: Stock/options trading and order management tests"
# Tools: buy_stock_*, sell_stock_*, buy_option_*, sell_option_*, stock_orders,
#        options_orders, open_stock_orders, open_option_orders, cancel_*
```

#### 5. **Options Analysis Journey**
```python
"journey_options: Options chains, market data, and position analysis tests"  
# Tools: options_chains, find_options, option_market_data, option_historicals,
#        aggregate_option_positions, all_option_positions, open_option_positions
```

#### 6. **Research & Analytics Journey**
```python
"journey_research: Earnings, ratings, news, and fundamental analysis tests"
# Tools: stock_earnings, stock_ratings, stock_news, stock_splits, stock_events,
#        dividends, dividends_by_instrument, total_dividends
```

#### 7. **Watchlist Management Journey**
```python
"journey_watchlists: Watchlist creation, management, and performance tracking tests"
# Tools: all_watchlists, watchlist_by_name, add_to_watchlist, 
#        remove_from_watchlist, watchlist_performance
```

#### 8. **Market Intelligence Journey**
```python
"journey_market_intelligence: Market movers, trends, and discovery tests"
# Tools: top_movers, top_movers_sp500, top_100_stocks, stocks_by_tag
```

#### 9. **Advanced Data Journey**
```python
"journey_advanced_data: Level II data, advanced instruments, and premium features tests"
# Tools: pricebook_by_symbol, stock_level2_data, interest_payments, 
#        stock_loan_payments
```

#### 10. **Notifications & Alerts Journey**
```python
"journey_notifications: Account notifications, alerts, and communication tests"
# Tools: notifications, latest_notification, margin_calls, margin_interest,
#        subscription_fees, referrals
```

#### 11. **System Health Journey**
```python
"journey_system: MCP server health, monitoring, and system status tests"
# Tools: health_check, metrics_summary, rate_limit_status, session_status
```

## 🚀 Implementation Plan

### Phase 1: Core Infrastructure
1. **Update conftest.py** with pytest_configure function and all markers
2. **Update pyproject.toml** with comprehensive marker definitions  
3. **Create base fixtures** for each journey type
4. **Add journey decorators** to existing tests

### Phase 2: Journey-Based Test Organization
1. **Reorganize existing tests** by journey markers
2. **Create journey-specific fixtures** (account data, market data, etc.)
3. **Add journey test utilities** (helpers, mocks, assertions)
4. **Document journey testing patterns**

### Phase 3: Advanced Journey Testing
1. **Cross-journey integration tests** (e.g., portfolio + market_data)
2. **Journey-specific performance tests**
3. **Journey error handling and recovery tests**
4. **Journey rate limiting and timeout tests**

## 📁 Proposed Test Structure

```
tests/
├── conftest.py                    # Journey markers and fixtures
├── unit/                          # @pytest.mark.unit
│   ├── test_account_journey.py    # @pytest.mark.journey_account  
│   ├── test_portfolio_journey.py  # @pytest.mark.journey_portfolio
│   ├── test_market_data_journey.py # @pytest.mark.journey_market_data
│   └── ...
├── integration/                   # @pytest.mark.integration
│   ├── test_trading_journey.py    # @pytest.mark.journey_trading
│   ├── test_options_journey.py    # @pytest.mark.journey_options
│   └── ...
└── performance/                   # @pytest.mark.performance
    ├── test_market_intelligence_journey.py
    └── ...
```

## 🏃‍♂️ Example Usage Commands

```bash
# Test specific user journeys
pytest -m "journey_account"                    # Account management only
pytest -m "journey_portfolio"                  # Portfolio and holdings only  
pytest -m "journey_market_data"                # Market data retrieval only
pytest -m "journey_trading"                    # Trading operations only

# Test multiple related journeys
pytest -m "journey_account or journey_portfolio"     # User account flows
pytest -m "journey_market_data or journey_research"  # Market intelligence flows

# Exclude slow/problematic journeys
pytest -m "not journey_trading and not slow"         # Skip trading and slow tests
pytest -m "journey_market_data and not rate_limited" # Market data without API limits

# Focus on READ ONLY journeys (for ADK evaluations)
pytest -m "journey_account or journey_portfolio or journey_market_data or journey_research or journey_watchlists or journey_notifications or journey_system"

# Performance testing by journey
pytest -m "journey_market_data and performance"      # Market data performance only

# Integration testing with authentication
pytest -m "integration and auth_required"            # Full integration with auth
```

## 🔧 Configuration Benefits

### 1. **Faster Feedback Loops**
- Test specific functionality without running entire suite
- Avoid timeout issues by focusing on relevant journey
- Parallel testing of independent journeys

### 2. **Better Test Organization** 
- Logical grouping by user workflow
- Clear separation of concerns
- Easy to find and maintain related tests

### 3. **Flexible CI/CD**
- Different pipeline stages for different journeys
- Conditional testing based on changes
- Performance testing isolation

### 4. **Developer Experience**
- Quick validation of specific features
- Focused debugging and development
- Clear test coverage by journey

## 📊 Expected Coverage Distribution

```
Journey Distribution (estimated):
- journey_account: ~15 tests (account info, profiles, settings)
- journey_portfolio: ~12 tests (portfolio, positions, holdings) 
- journey_market_data: ~18 tests (quotes, search, instruments)
- journey_research: ~14 tests (earnings, news, ratings, dividends)
- journey_watchlists: ~8 tests (watchlist CRUD, performance)
- journey_options: ~16 tests (chains, positions, market data)  
- journey_notifications: ~10 tests (alerts, margin, fees)
- journey_system: ~8 tests (health, metrics, session)
- journey_advanced_data: ~6 tests (Level II, premium features)
- journey_market_intelligence: ~5 tests (movers, trends)
- journey_trading: ~20 tests (orders, execution, cancellation)

Total: ~132 tests across 11 user journeys
```

## 🎯 Success Metrics

1. **Test Execution Time**: <30s per journey (vs current full suite)
2. **Test Coverage**: 95%+ for each journey independently  
3. **Failure Isolation**: Journey failures don't block other journeys
4. **CI/CD Efficiency**: Parallel journey testing reduces pipeline time
5. **Developer Productivity**: Quick iteration on specific features

This approach mirrors the successful pattern from open-paper-trading-mcp while being tailored to the specific MCP tool categories and user workflows in open-stocks-mcp.