# Packaging and Distribution

This document describes how to package and distribute the open-stocks-mcp project.

## Building the Package

### Using UV (Recommended)

```bash
# Build both wheel and source distribution
uv build

# Output will be in dist/
# - open_stocks_mcp-0.0.2-py3-none-any.whl (wheel)
# - open_stocks_mcp-0.0.2.tar.gz (source distribution)
```

### Using pip-tools

```bash
# Install build tools
pip install build

# Build the package
python -m build
```

## Installing the Package

### From PyPI (when published)

```bash
# Using UV
uv pip install open-stocks-mcp

# Using pip
pip install open-stocks-mcp
```

### From Local Build

```bash
# Using UV
uv pip install dist/open_stocks_mcp-0.0.2-py3-none-any.whl

# Using pip
pip install dist/open_stocks_mcp-0.0.2-py3-none-any.whl
```

### Development Installation

```bash
# Using UV (recommended)
uv pip install -e ".[dev]"

# Using pip
pip install -e ".[dev]"
```

## Publishing to PyPI

### Prerequisites

1. Create an account on [PyPI](https://pypi.org)
2. Generate an API token
3. Install twine: `uv pip install twine`

### Publishing

```bash
# Test on TestPyPI first
twine upload --repository testpypi dist/*

# Publish to PyPI
twine upload dist/*
```

### Using UV to publish (when supported)

UV may add publishing support in the future. Check the UV documentation for updates.

## Version Management

The version is defined in `src/open_stocks_mcp/__init__.py`:

```python
__version__ = "0.0.2"
```

To bump the version:
1. Update `__version__` in `src/open_stocks_mcp/__init__.py`
2. Update `version` in `pyproject.toml`
3. Commit the changes
4. Tag the release: `git tag v0.0.2`
5. Push the tag: `git push origin v0.0.2`

## Package Structure

The package includes:
- Python source code in `src/open_stocks_mcp/`
- Type hints (py.typed file included)
- Entry points for CLI commands:
  - `open-stocks-mcp`: Main server command
  - `open-stocks-mcp-server`: Server-specific command
  - `open-stocks-mcp-client`: Client command
- All dependencies specified in pyproject.toml

## Testing Installation

After building, test the installation in a fresh environment:

```bash
# Create a test environment
uv venv test-env
source test-env/bin/activate

# Install the wheel
uv pip install dist/open_stocks_mcp-0.0.2-py3-none-any.whl

# Test the command
open-stocks-mcp --help

# Test importing
python -c "import open_stocks_mcp; print(open_stocks_mcp.__version__)"
```