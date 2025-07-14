# Contributing to Open Stocks MCP

Thank you for your interest in contributing! We welcome contributions from everyone.

## Development Setup

### Prerequisites
- Python 3.11+
- [UV](https://docs.astral.sh/uv/) for dependency management
- Git for version control

### Setup
1. Fork and clone the repository:
   ```bash
   git clone https://github.com/Open-Agent-Tools/open-stocks-mcp.git
   cd open-stocks-mcp
   ```

2. Create virtual environment and install dependencies:
   ```bash
   uv venv && source .venv/bin/activate
   uv pip install -e ".[dev]"
   uv run pre-commit install
   ```

## Development Workflow

### Making Changes
1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes with tests and documentation updates

3. Run quality checks:
   ```bash
   uv run ruff check . --fix
   uv run ruff format .
   uv run mypy .
   uv run pytest -m "not slow and not exception_test"
   ```

4. Commit and push:
   ```bash
   git add .
   git commit -m "feat: your descriptive commit message"
   git push origin feature/your-feature-name
   ```

5. Create a pull request on GitHub

## Code Guidelines

### Code Style
- Follow PEP 8 (enforced by Ruff)
- Use type hints for all functions
- Maintain zero MyPy errors
- Write descriptive commit messages

### Testing
- Add unit tests for new functionality
- Use `@pytest.mark.integration` for tests requiring credentials
- Use `@pytest.mark.slow` for long-running tests
- Mock external API calls in unit tests

### MCP Tool Development
All MCP tools should follow this pattern:
```python
@mcp.tool()
async def tool_name(param: str) -> dict[str, Any]:
    """Clear description of what the tool does."""
    try:
        result = await execute_with_retry(rh.some_function, param)
        return {"result": result}
    except Exception as e:
        return {"result": {"error": str(e), "status": "error"}}
```

### Key Conventions
- Use async wrappers for Robin Stocks API
- Include retry logic via `execute_with_retry`
- Handle errors with `@handle_robin_stocks_errors`
- Return JSON with `{"result": data}` format
- Respect rate limiting

## Project Structure

```
src/open_stocks_mcp/
├── server/           # MCP server implementation
├── tools/            # MCP tool modules
├── auth/             # Authentication and session management
└── utils/            # Utilities and helpers

tests/
├── unit/             # Fast isolated tests
├── integration/      # Live API tests (requires credentials)
├── auth/             # Authentication tests
└── evals/            # ADK evaluation tests
```

## Testing

### Environment Variables
For integration tests, set:
```bash
ROBINHOOD_USERNAME="email@example.com"
ROBINHOOD_PASSWORD="password"
```

### Test Commands
```bash
pytest                           # All tests
pytest tests/unit/               # Unit tests only
pytest -m integration           # Integration tests
pytest -m "not slow and not exception_test"  # Fast tests (recommended)
```

## Documentation

- Update CLAUDE.md for development guidance
- Update README.md for user-facing changes
- Add docstrings to all public functions
- Include examples in tool descriptions

## Release Process

1. Update version in `pyproject.toml` and `src/open_stocks_mcp/__init__.py`
2. Update CHANGELOG.md with release notes
3. Create and push release tag
4. GitHub Actions will automatically publish to PyPI

## Questions or Issues?

- Open an issue on GitHub for bugs or feature requests
- Check existing issues before creating new ones
- Include minimal reproduction steps for bugs
- Provide context and use cases for feature requests

## License

By contributing, you agree that your contributions will be licensed under the MIT License.