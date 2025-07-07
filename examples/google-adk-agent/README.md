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
# and have access to auto_login and pass_through_mfa tools

# Example interaction:
# User: "Help me login to Robinhood"
# Agent: Will guide through username, password, and SMS MFA process
```

## Available Tools

Currently available through the MCP server:

- **`auto_login`**: Automatically initiate login process (checks environment credentials and triggers SMS)
- **`pass_through_mfa`**: Complete login with MFA code from SMS

## Agent Capabilities

The Stock_Trader agent specializes in:

**Authentication:**
- Guide users through Robinhood login process
- Handle SMS MFA authentication
- Manage session state

**Testing:**
- Validate tool functionality

**Future Capabilities:**
- Stock quotes and market data
- Portfolio management
- Trade execution
- Market analysis

## Example Interactions

1. **Automatic Login:**
   - **User:** "Login to my Robinhood account"
   - **Agent:** *Uses auto_login to check environment credentials and trigger SMS, then asks user for MFA code*

2. **Account Status:**
   - **User:** "Check my account status"
   - **Agent:** *Uses available tools to verify authentication state*