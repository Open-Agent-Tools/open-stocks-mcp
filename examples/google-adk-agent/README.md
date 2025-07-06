# Stock Trading Agent (Google ADK + MCP)

A specialized stock trading agent that uses Google ADK to connect with our open-stocks-mcp server for Robin Stocks operations.

## Prerequisites

1. **Install Google ADK**: Follow Google's Agent Development Kit installation guide
2. **Install open-stocks-mcp**: This package should be available in your environment
3. **Set up environment variables**:
   ```bash
   export GOOGLE_API_KEY="your-google-api-key"
   export GOOGLE_MODEL="gemini-2.0-flash"  # Optional, defaults to gemini-2.0-flash
   ```

## Usage

```python
from examples.google_adk_agent import root_agent

# The agent will automatically connect to the MCP server
# and have access to login_robinhood and echo tools

# Example interaction:
# User: "Help me login to Robinhood"
# Agent: Will guide through username, password, and SMS MFA process
```

## Available Tools

Currently available through the MCP server:

- **`echo`**: Test connectivity with case transformation options
- **`login_robinhood`**: Authenticate with Robinhood using:
  - Username (email)
  - Password
  - SMS MFA code (6-digit code received via text)

## Agent Capabilities

The Stock_Trader agent specializes in:

**Authentication:**
- Guide users through Robinhood login process
- Handle SMS MFA authentication
- Manage session state

**Testing:**
- Test MCP server connectivity
- Validate tool functionality

**Future Capabilities:**
- Stock quotes and market data
- Portfolio management
- Trade execution
- Market analysis

## Example Interactions

1. **Login Authentication:**
   - **User:** "Login to my Robinhood account"
   - **Agent:** *Guides through username, password, and SMS MFA process*

2. **Connection Test:**
   - **User:** "Test the connection"
   - **Agent:** *Uses echo tool to verify MCP server connectivity*

3. **Account Status:**
   - **User:** "Check my account status"
   - **Agent:** *Uses available tools to verify authentication state*