# Contributing to open-stocks-mcp

Thank you for your interest in contributing to open-stocks-mcp! We welcome contributions from everyone.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [UV](https://docs.astral.sh/uv/) for dependency management
- Git for version control

### Development Setup

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/Open-Agent-Tools/open-stocks-mcp.git
   cd open-stocks-mcp
   ```

3. Create a virtual environment and install dependencies:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e ".[dev]"
   ```

4. Install pre-commit hooks:
   ```bash
   uv run pre-commit install
   ```

## Development Workflow

### Creating a Branch

Create a new branch for your feature or bugfix:
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bugfix-name
```

### Making Changes

1. Make your changes in the appropriate files
2. Add or update tests as needed
3. Update documentation if you're changing behavior

### Code Style

We use several tools to maintain code quality:

- **Ruff** for linting and formatting
- **Black** for additional formatting (if needed)
- **MyPy** for type checking

Run these before committing:
```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy .
```

Or let pre-commit handle it automatically when you commit.

### Testing

Run the test suite before submitting:
```bash
# Run all tests
uv run pytest

# Run tests excluding slow ones
uv run pytest -m "not slow"

# Run only integration tests (may require credentials)
uv run pytest -m integration

# Run specific test file
uv run pytest tests/test_specific.py

# Run tests matching a pattern
uv run pytest -k "test_stock"
```

### Committing Changes

Write clear, concise commit messages:
```bash
git add .
git commit -m "feat: add real-time stock price updates"
# or
git commit -m "fix: handle empty portfolio response"
```

Follow conventional commits format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting changes
- `refactor:` for code refactoring
- `test:` for test additions/changes
- `chore:` for maintenance tasks

## Submitting a Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Go to the original repository on GitHub and create a Pull Request

3. Fill out the PR template with:
   - Clear description of changes
   - Related issue numbers (if any)
   - Test results
   - Any breaking changes

4. Wait for review and address any feedback

## Pull Request Guidelines

- PRs should focus on a single feature or fix
- Include tests for new functionality
- Update documentation as needed
- Ensure all tests pass
- Keep commits clean and atomic
- Rebase on main if needed to avoid merge conflicts

## Code Guidelines

### Type Hints

Always use type hints:
```python
def get_stock_price(symbol: str, exchange: str = "NYSE") -> float:
    """Get current stock price."""
    ...
```

### Docstrings

Use Google-style docstrings:
```python
def process_order(order: Order) -> OrderResult:
    """Process a stock order.
    
    Args:
        order: The order to process
        
    Returns:
        Result of the order processing
        
    Raises:
        InvalidOrderError: If the order is invalid
    """
```

### Error Handling

Be explicit about errors:
```python
try:
    result = api_call()
except SpecificError as e:
    logger.error(f"API call failed: {e}")
    raise ProcessingError(f"Could not process: {e}") from e
```

### Testing

Write tests for all new functionality:
```python
def test_stock_price_retrieval():
    """Test that stock prices are retrieved correctly."""
    price = get_stock_price("AAPL")
    assert isinstance(price, float)
    assert price > 0
```

## Areas for Contribution

- **New Tools**: Add MCP tools for additional stock market functionality
- **Documentation**: Improve docs, add examples, fix typos
- **Testing**: Increase test coverage, add edge cases
- **Performance**: Optimize slow operations
- **Bug Fixes**: Fix reported issues
- **Features**: Implement requested features from issues

## Questions?

- Check existing issues and discussions
- Create a new issue for bugs or feature requests
- Start a discussion for general questions
- Tag maintainers if you need help

## Code of Conduct

Please be respectful and constructive in all interactions. We aim to create a welcoming environment for all contributors.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.