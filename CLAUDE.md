# CLAUDE.md

Project guidance for Claude Code when working with the Open Stocks MCP server.

## User Shortcuts

### `cleanup`
Complete code quality workflow:
1. `uv run ruff check . --fix` - Fix linting issues
2. `uv run ruff format .` - Format code  
3. `uv run mypy .` - Type checking
4. `uv run pytest` - Run tests
5. Commit changes with detailed message

### `test`
Run test suite:
1. `uv run pytest` - All tests
2. `uv run pytest -m "not slow"` - Fast tests only
3. `uv run pytest -m integration` - Integration tests (needs credentials)

### `adk-eval`
Run ADK agent evaluation (from project root):
1. Verify ADK installed: `adk --help`
2. Set env vars: `GOOGLE_API_KEY`, `ROBINHOOD_USERNAME`, `ROBINHOOD_PASSWORD` 
3. Run: `adk eval examples/google-adk-agent tests/evals/list_available_tools_test.json --config_file_path tests/evals/test_config.json`

### `publish <version>`
Release workflow:
1. Run `cleanup` first
2. Update versions in `pyproject.toml` and `__init__.py`
3. `uv build` - Test package build
4. `gh release create v<version>` - Trigger PyPI publishing

### `check`
Quick project status:
1. `git status` - Working tree status
2. `git log --oneline -3` - Recent commits
3. `gh run list --limit=3` - CI status
4. `uv build` - Package build test

## Project Overview

**Open Stocks MCP** - Model Context Protocol server providing stock market data through Robin Stocks API.
- **Framework**: FastMCP for simplified MCP development
- **API**: Robin Stocks for market data and trading
- **Tools**: 60+ MCP tools for account, market data, options, orders
- **Agent Integration**: Google ADK evaluation tests

## Quick Reference

### Development Setup
```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Testing
```bash
pytest                           # All tests
pytest tests/unit/               # Unit tests (fast)
pytest tests/integration/ -m integration  # Integration (needs auth)
pytest tests/evals/ -m agent_evaluation   # ADK evaluation
```

### Code Quality
```bash
ruff check . --fix              # Lint and fix
ruff format .                   # Format code  
mypy .                          # Type check
```

### MCP Development
```bash
# Test server locally
uv run mcp dev src/open_stocks_mcp/server/app.py

# Test tools individually  
uv run python -c "from open_stocks_mcp.tools.robinhood_account_tools import get_account_info; print(get_account_info())"
```

## MCP Architecture

### Tool Structure
All tools return JSON with `result` field:
```python
@mcp.tool()
async def get_stock_quote(symbol: str) -> dict:
    try:
        quote = await execute_with_retry(rh.stocks.get_quote, symbol)
        return {"result": {"symbol": symbol, "price": float(quote["last_trade_price"])}}
    except Exception as e:
        return {"result": {"error": str(e), "status": "error"}}
```

### Key Patterns
- **Async wrappers** for Robin Stocks (synchronous API)
- **Retry logic** via `execute_with_retry`
- **Error handling** via `@handle_robin_stocks_errors` 
- **Rate limiting** via `get_rate_limiter()`
- **Session management** for authentication

### Authentication
```python
# Server startup authentication
from open_stocks_mcp.tools.session_manager import get_session_manager

session_manager = get_session_manager()
session_manager.set_credentials(username, password)
await session_manager.ensure_authenticated()
```

## Test Structure

```
tests/
├── unit/           # Fast isolated tests (18 tests)
├── auth/           # Authentication tests (29 tests) 
├── server/         # MCP server tests (10 tests)
├── integration/    # Live API tests (4 tests)
└── evals/          # ADK agent tests (1 test)
```

**Test Markers:**
- `slow` - Long-running tests
- `integration` - Requires credentials
- `agent_evaluation` - ADK evaluation tests

## GitHub Workflows

### Publishing
Triggered by release creation:
```bash
gh release create v0.3.1 --title "v0.3.1" --notes "Release notes"
```

### Development
```bash
gh repo view                    # Repository info
gh run list                     # Workflow status
gh pr create --title "feat: ..." --body "..."
```

## Environment Variables

### Required for Live Testing
```bash
ROBINHOOD_USERNAME="email@example.com"
ROBINHOOD_PASSWORD="password"
```

### Required for ADK Evaluation  
```bash
GOOGLE_API_KEY="your-google-api-key"
ROBINHOOD_USERNAME="email@example.com" 
ROBINHOOD_PASSWORD="password"
```

## Common Tasks

### Adding New MCP Tool
1. Create tool function in appropriate `tools/robinhood_*.py` file
2. Use `@mcp.tool()` decorator
3. Follow async pattern with error handling
4. Add to server registration in `server/app.py`
5. Write unit tests in `tests/unit/`

### Debugging Authentication Issues
1. Check session status: `session_manager.get_session_info()`
2. Test login: `session_manager.ensure_authenticated()`
3. Verify credentials in environment variables
4. Check Robin Stocks API status

### Running ADK Evaluations
1. Install: `pip install google-agent-developer-kit`
2. Set environment variables (see above)
3. From project root: `adk eval examples/google-adk-agent tests/evals/list_available_tools_test.json --config_file_path tests/evals/test_config.json`
4. Expected: "✅ Passed" with tool listing evaluation

## Important Notes

- **Always run ADK from project root** - Path resolution requirement
- **Use UV for dependencies** - Project uses UV package manager  
- **Async patterns required** - Robin Stocks is sync, tools are async
- **JSON responses mandatory** - All tools return `{"result": data}` format
- **Error handling critical** - Use decorators and try/catch patterns
- **Rate limiting active** - Automatic rate limiting for Robin Stocks API