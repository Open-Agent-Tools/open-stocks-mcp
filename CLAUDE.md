# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## User Shortcuts

When users type these commands, execute the associated actions:

### `cleanup`
Run complete code quality checks and fix all issues:
1. **Run ruff linting**: `uv run ruff check . --fix`
2. **Run ruff formatting**: `uv run ruff format .`
3. **Run mypy type checking**: `uv run mypy .` (fix any errors found)
4. **Run pytest**: `uv run pytest` (fix any failing tests)
5. **Review and update**: Check all TODO.md files for recent changes and update them
6. **Commit changes**: Make detailed commit with all fixes and push to current branch

### `publish`
Prepare and trigger a new release:
1. **Run cleanup first**: Execute all cleanup steps
2. **Check version**: Verify version in pyproject.toml and __init__.py match
3. **Build test**: Run `uv build` to ensure package builds correctly
4. **Create release**: Use `gh release create` with appropriate version and notes
5. **Monitor**: Track the publishing workflow with `gh run list`

### `test`
Run comprehensive testing:
1. **Run all tests**: `uv run pytest`
2. **Run excluding slow**: `uv run pytest -m "not slow"`
3. **Run integration tests**: `uv run pytest -m integration` (if credentials available)
4. **Report results**: Show test coverage and any failures

### `check`
Quick status check:
1. **Git status**: Show current branch and uncommitted changes
2. **Recent commits**: Show last 3 commits with `git log --oneline -3`
3. **Workflow status**: Check latest GitHub Actions with `gh run list --limit=3`
4. **Package status**: Check if package builds with `uv build`

## Project Overview

This is an MCP (Model Context Protocol) Server that provides access to stock market data through open-source APIs, particularly Robin Stocks. The server uses FastMCP for simplified MCP server development.

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
pytest
```

### Linting and Type Checking
```bash
ruff check .  # Linting
ruff format .  # Formatting
black .  # Alternative formatting
mypy .  # Type checking
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

1. **Structured Output**: Tools can return Pydantic models, TypedDicts, or regular dicts for structured data
2. **Context Access**: Tools can access MCP context for logging, progress reporting, and session data
3. **Async Support**: Use async functions for I/O operations
4. **Error Handling**: Raise exceptions with meaningful messages - they'll be properly formatted for clients

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

## GitHub CLI Usage

This project has GitHub CLI (gh) available and authenticated. Use it for repository operations:

### Repository Management
```bash
# View repository info
gh repo view

# Check workflow status
gh run list

# View latest workflow run
gh run view

# Re-run failed workflows
gh run rerun <run-id>
```

### Releases and Publishing
```bash
# Create a release (triggers PyPI publishing workflow)
gh release create v0.0.2 --title "v0.0.2 - Initial Release" --notes "Initial MCP server setup"

# List releases
gh release list

# View release details
gh release view v0.0.2
```

### Issues and Pull Requests
```bash
# Create an issue
gh issue create --title "Add Robin Stocks integration" --body "Implement stock price tools"

# List issues
gh issue list

# Create a pull request
gh pr create --title "feat: add stock price tool" --body "Implements get_stock_price tool using Robin Stocks API"

# View PR status
gh pr list
```

### Workflow Operations
```bash
# Trigger a workflow manually (if configured)
gh workflow run tests.yml

# View workflow runs
gh run list --workflow=tests.yml

# Download workflow artifacts
gh run download <run-id>
```

Always prefer `gh` commands over manual GitHub web interface operations for consistency and automation.

## Package Publishing

This project is configured for automated PyPI publishing via GitHub Actions with trusted publishing.

### Publishing Process

#### 1. Trigger Publishing via Release
```bash
# Create a new release to trigger publishing workflow
gh release create v0.0.2 --title "v0.0.2 - Feature Description" --notes "Release notes here"

# View the triggered workflow
gh run list --workflow=publish.yml

# Monitor specific run
gh run view <run-id>
```

#### 2. Manual Publishing (if needed)
```bash
# Build package locally
uv build

# Check package contents
ls dist/
# Should show: open_stocks_mcp-X.Y.Z.tar.gz and open_stocks_mcp-X.Y.Z-py3-none-any.whl

# Test package installation locally
uv pip install dist/open_stocks_mcp-*.whl
```

### Publishing Workflow

The GitHub Actions workflow (`publish.yml`) automatically:

1. **Build**: Creates wheel and source distribution
2. **Publish**: Uploads to PyPI using trusted publishing
3. **Artifacts**: Stores build artifacts for debugging

### Troubleshooting Publishing Issues

#### Common Workflow Failures

**Build Failures:**
```bash
# Check build job logs
gh run view <run-id> --job=build --log

# Common issues:
# - Missing dependencies in pyproject.toml
# - Import errors in package code
# - Version conflicts
```

**Publishing Failures:**
```bash
# Check publish job logs  
gh run view <run-id> --job="Publish to PyPI" --log

# Common issues:
# - PyPI trusted publishing not configured
# - Package name already exists
# - Version already published
# - Missing required metadata
```

#### Version Management Issues

**Version Already Exists:**
```bash
# Check current PyPI version
pip index versions open-stocks-mcp

# Update version in pyproject.toml and __init__.py
# Then create new release with updated version tag
```

**Version Mismatch:**
```bash
# Ensure version consistency between:
# - pyproject.toml [project] version
# - src/open_stocks_mcp/__init__.py __version__
# - git tag (should match)
```

#### PyPI Trusted Publishing Setup

If publishing fails with authentication errors:

1. **Go to PyPI.org** → Account → Publishing
2. **Add Pending Publisher:**
   - PyPI project name: `open-stocks-mcp`
   - Owner: `Open-Agent-Tools`
   - Repository: `open-stocks-mcp` 
   - Workflow: `publish.yml`
   - Environment: `pypi`

#### Local Testing Before Release

```bash
# Test package builds correctly
uv build

# Test installation from wheel
uv pip install --force-reinstall dist/open_stocks_mcp-*.whl

# Test CLI commands work
open-stocks-mcp --help
uv run pytest

# Test import works
python -c "import open_stocks_mcp; print(open_stocks_mcp.__version__)"
```

#### Debugging Workflow Issues

```bash
# Download workflow artifacts for inspection
gh run download <run-id>

# Check workflow file syntax
gh workflow view publish.yml

# Re-run failed workflow
gh run rerun <run-id>

# View workflow in browser
gh run view <run-id> --web
```

#### Emergency Publishing Recovery

If automated publishing fails completely:

```bash
# Manual publishing with twine (backup method)
uv build
uv pip install twine
twine upload dist/*
```

### Package Verification

After successful publishing:

```bash
# Verify package is available on PyPI
pip index versions open-stocks-mcp

# Test installation from PyPI
uv pip install open-stocks-mcp

# Verify CLI entry points
open-stocks-mcp --help
```

### Release Checklist

Before creating a release:

- [ ] Update version in `pyproject.toml` and `__init__.py`
- [ ] Run full test suite: `uv run pytest`
- [ ] Check code quality: `uv run ruff check . && uv run mypy .`
- [ ] Test local build: `uv build`
- [ ] Update CHANGELOG.md (if exists)
- [ ] Create meaningful release notes
- [ ] Tag follows semantic versioning (vX.Y.Z)