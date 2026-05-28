# Packaging and Distribution

This document describes how to package and distribute the open-stocks-mcp project.

## Building the Package

### Using UV (Recommended)

```bash
# Build both wheel and source distribution
uv build

# Output will be in dist/
# - open_stocks_mcp-0.6.5-py3-none-any.whl (wheel)
# - open_stocks_mcp-0.6.5.tar.gz (source distribution)
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
uv pip install dist/open_stocks_mcp-<version>-py3-none-any.whl

# Using pip
pip install dist/open_stocks_mcp-<version>-py3-none-any.whl
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
2. Configure trusted publishing for this repository in the `pypi` environment.
3. Ensure package version in `pyproject.toml` and `src/open_stocks_mcp/__init__.py` matches the release tag.

### Publishing workflow

Releases are published by GitHub Actions via [`.github/workflows/publish.yml`](../.github/workflows/publish.yml) when a GitHub Release is published.

```bash
# 1) Update versions and commit
git add pyproject.toml src/open_stocks_mcp/__init__.py
git commit -m "chore: bump version to <version>"

# 2) Create and push the tag
git tag v<version>
git push origin v<version>

# 3) Publish a GitHub Release for that tag
gh release create v<version> --generate-notes
```

The publish workflow validates tag/package version consistency, builds artifacts, and publishes to PyPI via trusted publishing.

## Version Management

The version is defined in `src/open_stocks_mcp/__init__.py`:

```python
__version__ = "0.6.5"
```

To bump the version:
1. Update `__version__` in `src/open_stocks_mcp/__init__.py`
2. Update `version` in `pyproject.toml`
3. Commit the changes
4. Tag the release: `git tag v<new-version>`
5. Push the tag: `git push origin v<new-version>`
6. Create a GitHub Release for that tag to trigger publish automation

## Package Structure

The package includes:
- Python source code in `src/open_stocks_mcp/`
- Type hints (py.typed file included)
- Entry points for CLI commands:
  - `open-stocks-mcp`: Main server command
  - `open-stocks-mcp-server`: Server-specific command
  - `open-stocks-mcp-client`: Testing client for calling MCP tools directly
- All dependencies specified in pyproject.toml

## Testing Installation

After building, test the installation in a fresh environment:

```bash
# Create a test environment
uv venv test-env
source test-env/bin/activate

# Install the wheel
uv pip install dist/open_stocks_mcp-<version>-py3-none-any.whl

# Test the command
open-stocks-mcp --help

# Test importing
python -c "import open_stocks_mcp; print(open_stocks_mcp.__version__)"
```
