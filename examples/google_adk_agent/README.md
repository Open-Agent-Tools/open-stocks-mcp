# Stock Trading Agent (Google ADK + MCP)

A comprehensive stock trading agent that uses Google ADK to connect with our open-stocks-mcp server for Robin Stocks and Schwab API operations. This agent provides access to 60+ MCP tools for complete stock market analysis and portfolio management across multiple brokers.

> **📁 Note**: Evaluation tests and documentation have been moved to `tests/evals/` for better organization alongside the main test suite. See `tests/evals/ADK-testing-evals.md` for comprehensive testing documentation.

## Prerequisites

1. **Install Google ADK**: Follow Google's Agent Development Kit installation guide
2. **Install open-stocks-mcp**: This package should be available in your environment
3. **Set up environment variables**:
   ```bash
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

   # MCP HTTP transport configuration
   export MCP_HTTP_URL="http://localhost:3001/mcp"  # Optional, defaults to localhost:3001
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
   MCP_HTTP_URL=http://localhost:3001/mcp
   ```

## Usage

The agent uses HTTP transport to connect to the MCP server, which must be running separately.

1. **Start the MCP server in HTTP mode:**
   ```bash
   open-stocks-mcp-server --transport http --port 3001
   ```

2. **Run your agent:**
   ```python
   from examples.google_adk_agent import root_agent
   
   # The agent will connect to the HTTP server
   # and have access to all stock trading tools
   
   # Example interaction:
   # User: "Show me my portfolio"
   # Agent: Will retrieve and display portfolio information
   ```

**Benefits of HTTP Transport:**
- Better timeout control and reliability
- Session management and persistence  
- Ability to run server and agent in separate processes
- Health check endpoints for monitoring
- Real-time connection status and error handling

## Available Tools

The agent has access to 60+ MCP tools organized into these categories:

### **Robinhood Account Management (5 tools)**
- **`account_info`**: Basic account information
- **`portfolio`**: Portfolio holdings and values
- **`account_details`**: Detailed account data (cash, buying power)
- **`positions`**: Current stock positions
- **`portfolio_history`**: Historical portfolio performance

### **Schwab Account Management (5 tools)**
- **`schwab_account_numbers`**: Account identifiers and hashes
- **`schwab_accounts`**: List of all Schwab accounts
- **`schwab_account`**: Specific account details
- **`schwab_portfolio`**: Account positions and holdings
- **`schwab_account_balances`**: Real-time account balances

### **Robinhood Order Management (2 tools)**
- **`stock_orders`**: Stock order history and status
- **`options_orders`**: Options order history

### **Schwab Order Management (3 tools)**
- **`schwab_orders`**: Account order history and status
- **`schwab_get_order`**: Specific order details
- **`schwab_cancel_order`**: Cancel an existing order

### **Robinhood Market Data (5 tools)**
- **`stock_price`**: Real-time stock prices
- **`stock_info`**: Company fundamentals
- **`search_stocks`**: Search for stocks by symbol/name
- **`market_hours`**: Market status and hours
- **`price_history`**: Historical price data

### **Schwab Market Data (5 tools)**
- **`schwab_quote`**: Real-time Schwab stock quote
- **`schwab_quotes`**: Batch Schwab quotes
- **`schwab_price_history`**: Historical price data from Schwab
- **`schwab_instrument`**: Instrument fundamental data
- **`schwab_search_instruments`**: Search for Schwab instruments

### **Options Trading (3 tools)**
- **`options_chains`**: Robinhood option chains
- **`schwab_option_chain`**: Schwab option chains
- **`schwab_option_expirations`**: Schwab option expiration dates

### **Advanced Market Data (10 tools)**
- **`top_movers_sp500`**: S&P 500 top movers
- **`top_100_stocks`**: Most popular stocks
- **`top_movers`**: Top 20 overall movers
- **`stocks_by_tag`**: Stocks by category (tech, biotech, etc.)
- **`stock_ratings`**: Analyst ratings
- **`stock_earnings`**: Earnings reports
- **`stock_news`**: Latest news stories
- **`stock_splits`**: Stock split history
- **`stock_events`**: Corporate events
- **`stock_level2_data`**: Level II market data (Gold)

### **Dividend & Income Tracking (5 tools)**
- **`dividends`**: Complete dividend history
- **`total_dividends`**: Total dividends with yearly breakdown
- **`dividends_by_instrument`**: Dividends for specific stocks
- **`interest_payments`**: Interest from cash management
- **`stock_loan_payments`**: Stock lending income

### **System Tools (5 tools)**
- **`list_tools`**: List all available tools
- **`session_status`**: Authentication status
- **`rate_limit_status`**: Rate limiting information
- **`metrics_summary`**: Performance metrics
- **`health_check`**: System health

## Agent Capabilities

The Stock_Trader agent specializes in:

### **Portfolio Management:**
- Comprehensive portfolio analysis with historical performance
- Real-time position tracking with current values
- Detailed account information including cash and buying power
- Order history and status monitoring

### **Market Analysis:**
- Real-time stock quotes and market data
- Top movers and trending stocks analysis
- Market category filtering (technology, biotech, etc.)
- Analyst ratings and earnings reports
- Latest news and corporate events

### **Income Tracking:**
- Complete dividend payment history
- Interest payments from cash management
- Stock lending program income tracking
- Yearly dividend analysis and trends

### **Market Intelligence:**
- S&P 500 movers and market trends
- Stock fundamentals and company information
- Historical price analysis
- Level II market data for advanced traders
- Stock splits and corporate events tracking

## Example Interactions

1. **Portfolio Analysis:**
   - **User:** "Show me my current holdings and their performance"
   - **Agent:** *Uses portfolio, positions, and portfolio_history to provide comprehensive analysis*

2. **Market Intelligence:**
   - **User:** "What are the top technology stocks moving today?"
   - **Agent:** *Uses stocks_by_tag("technology") and top_movers to identify trending tech stocks*

3. **Stock Research:**
   - **User:** "Tell me about Apple's recent performance and analyst ratings"
   - **Agent:** *Uses stock_info("AAPL"), stock_ratings("AAPL"), and stock_news("AAPL") for comprehensive analysis*

4. **Dividend Tracking:**
   - **User:** "How much have I earned in dividends this year?"
   - **Agent:** *Uses total_dividends to show yearly breakdown and dividend history*

5. **Market Overview:**
   - **User:** "What's happening in the market today?"
   - **Agent:** *Uses top_movers_sp500, market_hours, and top_100_stocks for market snapshot*

6. **Income Analysis:**
   - **User:** "Show me all my investment income sources"
   - **Agent:** *Uses dividends, interest_payments, and stock_loan_payments for complete income view*