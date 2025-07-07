# Stock Trading Agent (Google ADK + MCP)

A specialized stock trading agent that uses Google ADK to connect with our open-stocks-mcp server for Robin Stocks operations.

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

Currently available through the MCP server:

- **`get_portfolio`**: Retrieve current portfolio holdings and values
- **`get_stock_orders`**: Get list of stock orders and their status

## Agent Capabilities

The Stock_Trader agent specializes in:

**Portfolio Management:**
- View portfolio holdings and performance
- Track order history and status
- Monitor account values

**Testing:**
- Validate tool functionality

**Future Capabilities:**
- Stock quotes and market data
- Portfolio management
- Trade execution
- Market analysis

## Example Interactions

1. **Portfolio Overview:**
   - **User:** "Show me my current holdings"
   - **Agent:** *Uses get_portfolio to retrieve and display current positions*

2. **Order History:**
   - **User:** "What orders do I have pending?"
   - **Agent:** *Uses get_stock_orders to show order status and history*