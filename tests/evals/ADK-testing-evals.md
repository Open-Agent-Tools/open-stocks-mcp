# ADK Testing and Evaluations Guide

This guide covers testing and evaluation procedures for the Stock Trading Agent using Google ADK framework.

**Note**: This documentation and evaluation tests have been moved from `examples/google_adk_agent/evals/` to `tests/evals/` for better organization alongside the main test suite.

## Prerequisites

### 1. Environment Setup
```bash
# Set required environment variables
export GOOGLE_API_KEY="your-google-api-key"
export GOOGLE_MODEL="gemini-2.0-flash"  # Optional, defaults to gemini-2.0-flash

# For Robinhood authentication (optional - enables environment-based login)
export ROBINHOOD_USERNAME="your_email@example.com"
export ROBINHOOD_PASSWORD="your_robinhood_password"

# For Schwab authentication (optional - enables Schwab tools)
export SCHWAB_API_KEY="your-schwab-api-key"
export SCHWAB_APP_SECRET="your-schwab-app-secret"
export SCHWAB_CALLBACK_URL="https://127.0.0.1"
export SCHWAB_TOKEN_PATH="schwab_token.json"
export ENABLED_BROKERS="robinhood,schwab"
```

Or create a `.env` file in the project root:
```
GOOGLE_API_KEY=your-google-api-key
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_robinhood_password
SCHWAB_API_KEY=your-schwab-api-key
SCHWAB_APP_SECRET=your-schwab-app-secret
SCHWAB_CALLBACK_URL=https://127.0.0.1
SCHWAB_TOKEN_PATH=schwab_token.json
ENABLED_BROKERS=robinhood,schwab
```

### 2. Install Dependencies
```bash
# From the google_adk_agent directory
pip install -r requirements.txt

# Verify ADK installation
adk --help
```

## Running ADK Evaluations

> **⚠️ Important**: Always run ADK evaluations from the **project root directory** (`/Users/wes/Development/open-stocks-mcp/`). The ADK expects the agent module path relative to the current working directory.

### ✅ Correct Way (From Project Root)
```bash
# Navigate to project root first
cd /Users/wes/Development/open-stocks-mcp

# Basic evaluation command (with recommended config)
adk eval examples/google_adk_agent tests/evals/0_list_available_tools_test.json --config_file_path tests/evals/test_config.json

# With custom configuration
adk eval examples/google_adk_agent tests/evals/0_list_available_tools_test.json --config_file_path tests/evals/test_config.json

# With detailed results output
adk eval examples/google_adk_agent tests/evals/0_list_available_tools_test.json --config_file_path tests/evals/test_config.json --print_detailed_results

# With specific run ID for tracking
adk eval examples/google_adk_agent tests/evals/0_list_available_tools_test.json --config_file_path tests/evals/test_config.json --run_id stock_trader_test_$(date +%s)

# With custom model
GOOGLE_MODEL="gemini-2.0-flash-exp" adk eval examples/google_adk_agent tests/evals/0_list_available_tools_test.json --config_file_path tests/evals/test_config.json
```

### ❌ Wrong Way (From Agent Directory)
```bash
# Don't do this - will cause path errors
cd examples/google_adk_agent
adk eval agent.py ../../tests/evals/0_list_available_tools_test.json  # ❌ Incorrect syntax
```

### 📋 Prerequisites Checklist
Before running evaluations, ensure:

1. **✅ Google ADK Installed**
   ```bash
   pip install google-agent-developer-kit
   adk --help  # Verify installation
   ```

2. **✅ Environment Variables Set**
   ```bash
   export GOOGLE_API_KEY="your-google-api-key"
   export ROBINHOOD_USERNAME="your_email@example.com"
   export ROBINHOOD_PASSWORD="your_robinhood_password"
   ```

3. **✅ Correct Working Directory**
   ```bash
   pwd  # Should show: /Users/wes/Development/open-stocks-mcp
   ```

4. **✅ Agent Module Available**
   ```bash
   ls examples/google_adk_agent/  # Should show: agent.py, __init__.py, etc.
   ```

### 🎯 Expected Results
A successful evaluation will show:
```
Using evaluation criteria: {'tool_trajectory_avg_score': 0.5, 'response_match_score': 0.5}
Running Eval: list_available_tools_test_set:list_available_tools_test
Result: ✅ Passed

*********************************************************************
Eval Run Summary
list_available_tools_test_set:
  Tests passed: 1
  Tests failed: 0
```

**Last Successful Run**: 2025-07-10T15:01:40Z

## Available Evaluation Tests

### 1. List Available Tools Test
**File**: `tests/evals/0_list_available_tools_test.json`  
**Purpose**: Validates that the agent can successfully list all available MCP tools  
**Expected Output**: Alphabetically sorted bullet list of all registered MCP tools. The canonical expected response is the `final_response.parts[].text` field inside `tests/evals/0_list_available_tools_test.json`; update that file when the registered tool set changes.

```bash
adk eval examples/google_adk_agent tests/evals/0_list_available_tools_test.json --config_file_path tests/evals/test_config.json
```

### 2. System & Monitoring Read-Only Evals (`0_sys_*`)

Read-only evals that exercise server-local MCP monitoring tools. These do not invoke any trading or order-placement paths.

- `tests/evals/0_sys_health_check_test.json` — exercises the `health_check` tool to report MCP server health.
- `tests/evals/0_sys_session_status_test.json` — exercises the `session_status` tool to inspect Robinhood session and authentication state.
- `tests/evals/0_sys_metrics_summary_test.json` — exercises the `metrics_summary` tool to retrieve observability counters and latency metrics.
- `tests/evals/0_sys_rate_limit_status_test.json` — exercises the `rate_limit_status` tool to inspect Robin Stocks API rate-limit usage.

These evals are strictly read-only: prompts and expected responses describe server state only, with no order placement, cancellation, or trading-path tools referenced. Because the four tools target server-local monitoring state, ADK execution requires `GOOGLE_API_KEY` and a reachable MCP server, but does **not** require live Robinhood credentials for these specific calls (the underlying Robin Stocks rate-limit counters track quota without performing a broker call).

Run with:

```bash
adk eval examples/google_adk_agent tests/evals/0_sys_health_check_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/0_sys_session_status_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/0_sys_metrics_summary_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/0_sys_rate_limit_status_test.json --config_file_path tests/evals/test_config.json
```

### 3. Account Evals (`1_acc_*`)

Read-only account evaluations for Robinhood portfolio, positions, and dividend tools. Require `ROBINHOOD_USERNAME` and `ROBINHOOD_PASSWORD`.

- `tests/evals/1_acc_account_info_test.json` — exercises `account_info`.
- `tests/evals/1_acc_account_details_test.json` — exercises `account_details`.
- `tests/evals/1_acc_portfolio_test.json` — exercises `portfolio`.
- `tests/evals/1_acc_positions_test.json` — exercises `positions`.
- `tests/evals/1_acc_build_holdings_test.json` — exercises `build_holdings`.
- `tests/evals/1_acc_dividends_test.json` — exercises `dividends`.
- `tests/evals/1_acc_total_dividends_test.json` — exercises `total_dividends`.
- `tests/evals/1_acc_dividends_by_instrument_test.json` — exercises `dividends_by_instrument`.
- `tests/evals/1_acc_day_trades_test.json` — exercises `day_trades`.
- `tests/evals/1_acc_interest_payments_test.json` — exercises `interest_payments`.
- `tests/evals/1_acc_stock_loan_payments_test.json` — exercises `stock_loan_payments`.
- `tests/evals/1_acc_health_check_test.json` — exercises the account-level `health_check`.

### Market & Research Read-Only Evaluations

Read-only market and research evaluations for Robinhood quote, discovery, price history, mover, analyst, earnings, news, and split tools.

**Credential assumptions**: requires GOOGLE_API_KEY and read-only ROBINHOOD_USERNAME/ROBINHOOD_PASSWORD; no order placement

These scenarios are read-only and must not place orders, cancel orders, buy, sell, or mutate watchlists.

- `tests/evals/2_mkt_stock_price_test.json` — exercises `stock_price` to retrieve a current stock price snapshot; run `adk eval examples/google_adk_agent tests/evals/2_mkt_stock_price_test.json --config_file_path tests/evals/test_config.json`.
- `tests/evals/2_mkt_stock_info_test.json` — exercises `stock_info` to retrieve company profile and market metadata; run `adk eval examples/google_adk_agent tests/evals/2_mkt_stock_info_test.json --config_file_path tests/evals/test_config.json`.
- `tests/evals/2_mkt_search_stocks_test.json` — exercises `search_stocks` to search for stocks by symbol or company name; run `adk eval examples/google_adk_agent tests/evals/2_mkt_search_stocks_test.json --config_file_path tests/evals/test_config.json`.
- `tests/evals/2_mkt_market_hours_test.json` — exercises `market_hours` to inspect exchange schedules and current market status; run `adk eval examples/google_adk_agent tests/evals/2_mkt_market_hours_test.json --config_file_path tests/evals/test_config.json`.
- `tests/evals/2_mkt_price_history_test.json` — exercises `price_history` to retrieve recent OHLC and volume data for a symbol; run `adk eval examples/google_adk_agent tests/evals/2_mkt_price_history_test.json --config_file_path tests/evals/test_config.json`.
- `tests/evals/2_mkt_top_movers_sp500_test.json` — exercises `top_movers_sp500` to list major S&P 500 market movers; run `adk eval examples/google_adk_agent tests/evals/2_mkt_top_movers_sp500_test.json --config_file_path tests/evals/test_config.json`.
- `tests/evals/2_mkt_top_100_stocks_test.json` — exercises `top_100_stocks` to retrieve popular Robinhood stocks; run `adk eval examples/google_adk_agent tests/evals/2_mkt_top_100_stocks_test.json --config_file_path tests/evals/test_config.json`.
- `tests/evals/2_mkt_top_movers_test.json` — exercises `top_movers` to retrieve broad-market gainers and losers; run `adk eval examples/google_adk_agent tests/evals/2_mkt_top_movers_test.json --config_file_path tests/evals/test_config.json`.
- `tests/evals/2_mkt_stock_ratings_test.json` — exercises `stock_ratings` to summarize analyst ratings for a symbol; run `adk eval examples/google_adk_agent tests/evals/2_mkt_stock_ratings_test.json --config_file_path tests/evals/test_config.json`.
- `tests/evals/2_mkt_stock_earnings_test.json` — exercises `stock_earnings` to retrieve recent earnings report data; run `adk eval examples/google_adk_agent tests/evals/2_mkt_stock_earnings_test.json --config_file_path tests/evals/test_config.json`.
- `tests/evals/2_mkt_stock_news_test.json` — exercises `stock_news` to retrieve recent symbol-specific news; run `adk eval examples/google_adk_agent tests/evals/2_mkt_stock_news_test.json --config_file_path tests/evals/test_config.json`.
- `tests/evals/2_mkt_stock_splits_test.json` — exercises `stock_splits` to retrieve stock split history for a symbol; run `adk eval examples/google_adk_agent tests/evals/2_mkt_stock_splits_test.json --config_file_path tests/evals/test_config.json`.

### 5. Profiles Tests (`6_prf_*`)

Read-only evaluations for Robinhood profile tools. All require `ROBINHOOD_USERNAME` and `ROBINHOOD_PASSWORD`.

- `tests/evals/6_prf_account_profile_test.json` — exercises `account_profile` to retrieve Robinhood account profile data.
- `tests/evals/6_prf_basic_profile_test.json` — exercises `basic_profile` to retrieve basic user information.
- `tests/evals/6_prf_investment_profile_test.json` — exercises `investment_profile` to retrieve investment objectives and risk tolerance.
- `tests/evals/6_prf_security_profile_test.json` — exercises `security_profile` to retrieve security/authentication profile data.
- `tests/evals/6_prf_user_profile_test.json` — exercises `user_profile` to retrieve user profile details.
- `tests/evals/6_prf_complete_profile_test.json` — exercises `complete_profile` to retrieve all profile data in one call.

Run with:

```bash
adk eval examples/google_adk_agent tests/evals/6_prf_account_profile_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/6_prf_basic_profile_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/6_prf_investment_profile_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/6_prf_security_profile_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/6_prf_user_profile_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/6_prf_complete_profile_test.json --config_file_path tests/evals/test_config.json
```

### 6. Options Data Evals (`8_opt_*`)

Evaluations for Robinhood options tools. Multi-step evals for `option_market_data` and `option_historicals` resolve an option contract via `options_chains` first (public data). The `aggregate_option_positions` and `open_option_positions_with_details` evals require `ROBINHOOD_USERNAME` and `ROBINHOOD_PASSWORD`.

- `tests/evals/8_opt_find_options_test.json` — exercises `find_options` and `options_chains`.
- `tests/evals/8_opt_options_chains_test.json` — exercises `options_chains` for TSLA.
- `tests/evals/8_opt_option_market_data_test.json` — multi-step: `options_chains` then `option_market_data` to retrieve live market data for a specific AAPL call option contract.
- `tests/evals/8_opt_option_historicals_test.json` — multi-step: `options_chains` then `option_historicals` to retrieve historical price data for an AAPL call option.
- `tests/evals/8_opt_aggregate_option_positions_test.json` — exercises `aggregate_option_positions` to show options exposure grouped by underlying (requires Robinhood credentials).
- `tests/evals/8_opt_open_option_positions_with_details_test.json` — exercises `open_option_positions_with_details` to list open positions with call/put details and Greeks (requires Robinhood credentials).

Run with:

```bash
adk eval examples/google_adk_agent tests/evals/8_opt_option_market_data_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/8_opt_option_historicals_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/8_opt_aggregate_option_positions_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/8_opt_open_option_positions_with_details_test.json --config_file_path tests/evals/test_config.json
```

### 7. Advanced Tests (`9_adv_*`)

Read-only evaluations for advanced aggregation and account management tools. `build_user_profile`, `account_settings`, and `account_features` require `ROBINHOOD_USERNAME` and `ROBINHOOD_PASSWORD`. `broker_status` does not require Robinhood credentials.

- `tests/evals/9_adv_build_user_profile_test.json` — exercises `build_user_profile` to retrieve aggregated equity, cash, and dividend totals.
- `tests/evals/9_adv_account_settings_test.json` — exercises `account_settings` to retrieve current account settings and configuration.
- `tests/evals/9_adv_account_features_test.json` — exercises `account_features` to list enabled account features and permissions.
- `tests/evals/9_adv_broker_status_test.json` — exercises `broker_status` to show connected brokers and their status.

Run with:

```bash
adk eval examples/google_adk_agent tests/evals/9_adv_build_user_profile_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/9_adv_account_settings_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/9_adv_account_features_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/9_adv_broker_status_test.json --config_file_path tests/evals/test_config.json
```

### 8. Schwab Market & Account Evals (`schwab_*`)

Evaluations for Schwab-specific tools. These typically require live Schwab OAuth credentials and a running MCP server.

- `tests/evals/1_acc_schwab_account_numbers_test.json` — exercises `schwab_account_numbers`.
- `tests/evals/2_mkt_schwab_quote_test.json` — exercises `schwab_quote`.
- `tests/evals/2_mkt_schwab_price_history_test.json` — exercises `schwab_price_history`.
- `tests/evals/2_mkt_schwab_search_instruments_test.json` — exercises `schwab_search_instruments`.
- `tests/evals/8_opt_schwab_option_chain_test.json` — exercises `schwab_option_chain`.
- `tests/evals/8_opt_schwab_option_expirations_test.json` — exercises `schwab_option_expirations`.
- `tests/evals/5_ord_schwab_orders_test.json` — multi-step: `schwab_account_numbers` then `schwab_orders` to retrieve recent orders without requiring a raw account hash in the user message.

> **Note on Schwab Evaluations**: Most Schwab evaluations require live OAuth credentials.
>
> The `final_response` examples in Schwab eval JSON files are illustrative placeholders only. Before running against a live Schwab account, update those expected values (account numbers, account hashes, quotes, and other account-specific fields) to match real output from your account, or ADK eval assertions will fail.

Run with:

```bash
adk eval examples/google_adk_agent tests/evals/1_acc_schwab_account_numbers_test.json --config_file_path tests/evals/test_config.json
SCHWAB_EVAL_FILE=<schwab-market-eval-json>
adk eval examples/google_adk_agent "tests/evals/${SCHWAB_EVAL_FILE}" --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/8_opt_schwab_option_chain_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/8_opt_schwab_option_expirations_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/5_ord_schwab_orders_test.json --config_file_path tests/evals/test_config.json
```

### 4. Watchlist Read-Only Evaluations (`3_wth_*`)

Read-only evals that exercise the three Robinhood watchlist query tools. These do not invoke `add_to_watchlist`, `remove_from_watchlist`, or any order-placement or account-mutation tool.

- `tests/evals/3_wth_all_watchlists_test.json` — exercises `all_watchlists` with empty args to list all account watchlists.
- `tests/evals/3_wth_watchlist_by_name_test.json` — exercises `watchlist_by_name` with `{"watchlist_name": "Tech Stocks"}` to retrieve contents of a named watchlist.
- `tests/evals/3_wth_watchlist_performance_test.json` — exercises `watchlist_performance` with `{"watchlist_name": "Tech Stocks"}` to analyze price and percentage changes for symbols in a named watchlist.

**Credential assumptions**: Requires `GOOGLE_API_KEY`, a running MCP server, and Robinhood read credentials. The `watchlist_by_name` and `watchlist_performance` scenarios assume a watchlist named `Tech Stocks` exists in the live account. Rename `watchlist_name` to an existing watchlist before running those two evals against a live account.

Run with:

```bash
adk eval examples/google_adk_agent tests/evals/3_wth_all_watchlists_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/3_wth_watchlist_by_name_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/3_wth_watchlist_performance_test.json --config_file_path tests/evals/test_config.json
```

### 5. Notifications and Account Features Read-Only Evaluations (`4_ntf_*`)

Read-only evals that exercise seven notification and account-feature query tools. These do not invoke any order-placement, watchlist-mutation, or account-modification tool. The live account may legitimately return empty or no-data responses for notifications, margin, fees, or referrals.

- `tests/evals/4_ntf_notifications_test.json` — exercises `notifications` with `{"count": 5}` to retrieve the five most recent account notifications.
- `tests/evals/4_ntf_latest_notification_test.json` — exercises `latest_notification` with empty args to retrieve the single most recent notification.
- `tests/evals/4_ntf_margin_calls_test.json` — exercises `margin_calls` with empty args to check for active margin calls.
- `tests/evals/4_ntf_margin_interest_test.json` — exercises `margin_interest` with empty args to retrieve margin interest charges and current rate.
- `tests/evals/4_ntf_subscription_fees_test.json` — exercises `subscription_fees` with empty args to retrieve Robinhood Gold subscription fee history.
- `tests/evals/4_ntf_referrals_test.json` — exercises `referrals` with empty args to retrieve referral program status.
- `tests/evals/4_ntf_account_features_test.json` — exercises `account_features` with empty args to summarize available subscription, margin, notification, and referral features; may return `partial_success` if one data source is unavailable.

**Credential assumptions**: Requires `GOOGLE_API_KEY`, a running MCP server, and Robinhood read credentials. All tools may return empty data on accounts without margin, Gold subscriptions, or referrals — this is an expected valid outcome, not a failure.

Run with:

```bash
adk eval examples/google_adk_agent tests/evals/4_ntf_notifications_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/4_ntf_latest_notification_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/4_ntf_margin_calls_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/4_ntf_margin_interest_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/4_ntf_subscription_fees_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/4_ntf_referrals_test.json --config_file_path tests/evals/test_config.json
adk eval examples/google_adk_agent tests/evals/4_ntf_account_features_test.json --config_file_path tests/evals/test_config.json
```


### 7. Creating Custom Evaluation Tests

#### Test File Structure
```json
{
  "eval_set_id": "your_test_set_id",
  "name": "Your Test Name",
  "description": "Description of what this test validates",
  "eval_cases": [
    {
      "eval_id": "your_test_case_id",
      "conversation": [
        {
          "invocation_id": "unique-invocation-id",
          "user_content": {
            "parts": [
              {
                "text": "Your test prompt here"
              }
            ],
            "role": "user"
          },
          "final_response": {
            "parts": [
              {
                "text": "Expected response from agent"
              }
            ],
            "role": "model"
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "id": "adk-tool-use-id",
                "args": {"param": "value"},
                "name": "tool_name"
              }
            ],
            "intermediate_responses": []
          }
        }
      ],
      "session_input": {
        "app_name": "stock_trader_agent",
        "user_id": "test_user",
        "state": {}
      }
    }
  ]
}
```

#### Example Test Cases to Create

1. **Portfolio Analysis Test**
```bash
# Test prompt: "Show me my current portfolio holdings"
# Expected tools: portfolio, positions, account_details
```

2. **Stock Research Test**
```bash
# Test prompt: "Tell me about Apple's stock performance and analyst ratings"
# Expected tools: stock_info, stock_price, stock_ratings, stock_news
```

3. **Market Overview Test**
```bash
# Test prompt: "What are the top S&P 500 movers today?"
# Expected tools: top_movers_sp500, market_hours
```

4. **Dividend Analysis Test**
```bash
# Test prompt: "How much have I earned in dividends this year?"
# Expected tools: total_dividends, dividends
```

## Evaluation Configuration

### Test Configuration File
**File**: `tests/evals/test_config.json`

```json
{
  "criteria": {
    "tool_trajectory_avg_score": 0.5,
    "response_match_score": 0.5
  }
}
```

### Scoring Criteria
- **tool_trajectory_avg_score**: Measures if the agent uses the correct tools in the right sequence
- **response_match_score**: Measures if the agent's response matches the expected output

## Troubleshooting

### Common Issues

#### 1. MCP Server Connection Issues
```bash
# Test MCP server directly
uv run open-stocks-mcp-server --transport stdio

# Check if server responds to list_tools
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | uv run open-stocks-mcp-server --transport stdio
```

#### 2. Authentication Errors
```bash
# Verify environment variables are set
echo "GOOGLE_API_KEY: ${GOOGLE_API_KEY:0:10}..."
echo "ROBINHOOD_USERNAME: $ROBINHOOD_USERNAME"

# Test Google API key
python3 -c "
import os
from google import genai
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
print('Google API key is valid')
"
```

#### 3. ADK Command Not Found
```bash
# Reinstall Google ADK
pip install --upgrade google-adk

# Verify installation
python3 -c "import google.adk; print('ADK installed successfully')"
```

#### 4. Tool Connection Issues
```bash
# Check if MCP server is accessible
python3 -c "
from examples.google_adk_agent.agent import create_agent
agent = create_agent()
print('Agent created successfully')
"
```



### Local Testing Script
```bash
#!/bin/bash
# test-all-evals.sh

set -e

echo "Running all ADK evaluations..."

# List available tools test
echo "Testing tool listing..."
adk eval examples/google_adk_agent tests/evals/0_list_available_tools_test.json --config_file_path tests/evals/test_config.json

# Add more tests as they are created
# echo "Testing portfolio analysis..."
# adk eval examples/google_adk_agent tests/evals/portfolio_analysis_test.json --config_file_path tests/evals/test_config.json

echo "All evaluations completed successfully!"
```

## Performance Monitoring

### Evaluation Metrics to Track
- **Tool Selection Accuracy**: How often the agent chooses the correct tools
- **Response Quality**: How well the agent's responses match expected outputs
- **Execution Time**: How long evaluations take to complete
- **Error Rate**: Frequency of evaluation failures

### Monitoring Script
```python
#!/usr/bin/env python3
"""Monitor ADK evaluation performance over time."""

import json
import time
import subprocess
from datetime import datetime

def run_evaluation(test_file):
    """Run a single evaluation and return results."""
    start_time = time.time()
    try:
        result = subprocess.run(
            ["adk", "eval", "examples/google_adk_agent", test_file, "--config_file_path", "tests/evals/test_config.json"],
            capture_output=True,
            text=True,
            check=True
        )
        duration = time.time() - start_time
        return {
            "success": True,
            "duration": duration,
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        return {
            "success": False,
            "duration": duration,
            "error": e.stderr
        }

if __name__ == "__main__":
    tests = ["tests/evals/0_list_available_tools_test.json"]
    
    for test in tests:
        print(f"Running {test}...")
        result = run_evaluation(test)
        
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] {test}: {'PASS' if result['success'] else 'FAIL'} ({result['duration']:.2f}s)")
        
        if not result['success']:
            print(f"Error: {result['error']}")
```

## Best Practices

### 1. Test Design
- Create tests that cover all major tool categories
- Include both positive and negative test cases
- Test edge cases and error conditions
- Validate tool parameter usage

### 2. Evaluation Maintenance
- Run evaluations regularly (CI/CD)
- Update expected outputs when tools change
- Monitor evaluation performance trends
- Add new tests for new features

### 3. Debugging
- Use verbose output for failing tests
- Check MCP server logs for connection issues
- Verify environment variables are correctly set
- Test individual tools outside of ADK framework

## Additional Resources

- [Google ADK Documentation](https://developers.google.com/agent-development-kit)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [Open Stocks MCP Documentation](../../README.md)
- [Stock Trading Agent Documentation](README.md)
