# GEMINI.md

This file provides technical guidance for Gemini when working with the Open Stocks MCP server codebase.

## Development Commands

This project uses UV for dependency management and virtual environments.

### Virtual Environment Setup
```bash
uv venv  # Creates .venv
source .venv/bin/activate  # Activate the environment
```

### Dependency Installation
```bash
uv pip install -e .  # Install project in editable mode
uv pip install -e ".[dev]"  # Install with dev dependencies
```

### Running Tests
```bash
uv run pytest
```

### Linting and Type Checking
```bash
uv run ruff check .  # Linting
uv run ruff format .  # Formatting
uv run mypy .  # Type checking
```

### Adding Dependencies
```bash
# Add to pyproject.toml dependencies section, then:
uv pip install -e .
```

## Architecture

### MCP Server Structure

The project uses FastMCP, which provides a high-level interface to the MCP protocol:

```python
from mcp.server.fastmcp import FastMCP

# Create server instance
mcp = FastMCP("Open Stocks MCP")

# Tools are functions that can have side effects
@mcp.tool()
def get_stock_price(symbol: str) -> dict:
    """Get current stock price."""
    return {"symbol": symbol, "price": 100.00}

# Resources provide data without side effects  
@mcp.resource("portfolio://holdings")
def get_holdings() -> str:
    """Get portfolio holdings."""
    return json.dumps({"AAPL": 10, "GOOGL": 5})

# Prompts are reusable templates
@mcp.prompt(title="Stock Analysis")
def analyze_stock(symbol: str) -> str:
    return f"Analyze {symbol} stock performance"
```

### Key MCP Patterns

1. **JSON Output**: Tools should ALWAYS return JSON objects with data in a "result" field
2. **Structured Output**: Tools can return Pydantic models, TypedDicts, or regular dicts for structured data
3. **Context Access**: Tools can access MCP context for logging, progress reporting, and session data
4. **Async Support**: Use async functions for I/O operations
5. **Error Handling**: Return JSON objects with error information in the "result" field

### MCP Tool Best Practices

When implementing MCP tools, follow these best practices:

1. **Clear Naming**: Provide clear, descriptive names and descriptions
2. **Schema Definitions**: Use detailed JSON Schema definitions for parameters
3. **Examples**: Include examples in tool descriptions to demonstrate usage
4. **Error Handling**: Implement proper error handling and validation
5. **Progress Reporting**: Use progress reporting for long operations
6. **Atomic Operations**: Keep tool operations focused and atomic
7. **Documentation**: Document expected return value structures
8. **Timeouts**: Implement proper timeouts for operations
9. **Rate Limiting**: Consider rate limiting for resource-intensive operations
10. **Logging**: Log tool usage for debugging and monitoring
11. **Result Field**: Always return JSON with data in a "result" field

Example tool implementation:

```python
@mcp.tool()
async def get_stock_quote(symbol: str) -> dict:
    """Get detailed stock quote information.
    
    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "GOOGL")
    
    Returns:
        JSON object with stock quote data in "result" field:
        {
            "result": {
                "symbol": "AAPL",
                "price": 150.00,
                "change": 2.50,
                "change_percent": 1.69,
                "volume": 50000000
            }
        }
    """
    try:
        # Async wrapper for synchronous API
        loop = asyncio.get_event_loop()
        quote = await loop.run_in_executor(None, rh.stocks.get_quote, symbol)
        
        return {
            "result": {
                "symbol": symbol,
                "price": float(quote["last_trade_price"]),
                "change": float(quote["previous_close"]) - float(quote["last_trade_price"]),
                "volume": int(quote["volume"]),
                "status": "success"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get quote for {symbol}: {e}")
        return {
            "result": {
                "error": str(e),
                "status": "error"
            }
        }
```

### Robin Stocks Integration

Robin Stocks is synchronous, so wrap calls in async functions:

```python
import asyncio
import robin_stocks.robinhood as rh

@mcp.tool()
async def get_stock_quote(symbol: str) -> dict:
    """Get stock quote asynchronously."""
    loop = asyncio.get_event_loop()
    quote = await loop.run_in_executor(None, rh.stocks.get_latest_price, symbol)
    return {"symbol": symbol, "price": float(quote[0])}
```

### Development Guidelines

1. **Tools vs Resources**: 
   - Tools: Functions that perform actions (place orders, fetch live data)
   - Resources: Static or cached data (portfolio snapshot, watchlists)

2. **Authentication**: Handle Robin Stocks auth in server lifecycle:
   ```python
   from contextlib import asynccontextmanager
   
   @asynccontextmanager
   async def app_lifespan(server: FastMCP):
       # Login on startup
       rh.login(username, password)
       yield
       # Logout on shutdown
       rh.logout()
   
   mcp = FastMCP("Open Stocks", lifespan=app_lifespan)
   ```

3. **Error Handling**: Always handle API errors gracefully
4. **Rate Limiting**: Implement caching to avoid hitting API limits
5. **Security**: Never log or return sensitive data (passwords, full account numbers)

## Testing MCP Tools

Test tools with the MCP Inspector:
```bash
uv run mcp dev src/open_stocks_mcp/server/app.py
```

Or write unit tests with pytest:
```python
def test_stock_tool():
    result = get_stock_price("AAPL")
    assert "symbol" in result
    assert "price" in result

@pytest.mark.integration
def test_live_stock_data():
    # Test requiring real API access
    pass

@pytest.mark.slow  
def test_performance():
    # Test that might take longer
    pass
```

Available test markers:
- `slow`: Tests that take longer to run
- `integration`: Tests requiring credentials/live APIs  
- `live_market`: Tests requiring live market data

## Release Management

For complete GitHub CLI operations and release processes, see `CONTRIBUTING.md`.
