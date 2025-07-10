# Stock Trading Agent (Google ADK + MCP)

A comprehensive stock trading agent that uses Google ADK to connect with our open-stocks-mcp server for Robin Stocks operations. This agent provides access to 32+ MCP tools for complete stock market analysis and portfolio management.

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
   ```

   Or create a `.env` file in the project root:
   ```
   GOOGLE_API_KEY=your-google-api-key
   ROBINHOOD_USERNAME=your_email@example.com
   ROBINHOOD_PASSWORD=your_robinhood_password
   ```

## Usage

```python
from examples.google_adk_agent import root_agent

# The agent will automatically connect to the MCP server
# and have access to stock trading tools

# Example interaction:
# User: "Show me my portfolio"
# Agent: Will retrieve and display portfolio information
```

## Available Tools

The agent has access to 32+ MCP tools organized into these categories:

### **Account Management (5 tools)**
- **`account_info`**: Basic account information
- **`portfolio`**: Portfolio holdings and values
- **`account_details`**: Detailed account data (cash, buying power)
- **`positions`**: Current stock positions
- **`portfolio_history`**: Historical portfolio performance

### **Order Management (2 tools)**
- **`stock_orders`**: Stock order history and status
- **`options_orders`**: Options order history

### **Stock Market Data (5 tools)**
- **`stock_price`**: Real-time stock prices
- **`stock_info`**: Company fundamentals
- **`search_stocks`**: Search for stocks by symbol/name
- **`market_hours`**: Market status and hours
- **`price_history`**: Historical price data

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