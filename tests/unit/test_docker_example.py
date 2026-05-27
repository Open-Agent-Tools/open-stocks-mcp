import pathlib
import re
import tomllib

import pytest

# Paths relative to the project root
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
DOCKERFILE_PATH = PROJECT_ROOT / "examples" / "open-stocks-mcp-docker" / "Dockerfile"
README_PATH = PROJECT_ROOT / "examples" / "open-stocks-mcp-docker" / "README.md"
APP_PY_PATH = PROJECT_ROOT / "src" / "open_stocks_mcp" / "server" / "app.py"


@pytest.mark.unit
@pytest.mark.journey_system
def test_dockerfile_version_matches_pyproject():
    """
    Verify that the Dockerfile defines a package version build arg
    that matches the current version in pyproject.toml.
    """
    # Read version from pyproject.toml
    with open(PYPROJECT_PATH, "rb") as f:
        pyproject_data = tomllib.load(f)
    expected_version = pyproject_data["project"]["version"]

    # Read Dockerfile content
    dockerfile_content = DOCKERFILE_PATH.read_text()

    # Assert ARG OPEN_STOCKS_MCP_VERSION=x.y.z exists and matches
    arg_line = f"ARG OPEN_STOCKS_MCP_VERSION={expected_version}"
    assert arg_line in dockerfile_content, (
        f"Dockerfile must contain '{arg_line}' to match project version."
    )


@pytest.mark.unit
@pytest.mark.journey_system
def test_dockerfile_uses_versioned_install():
    """
    Verify that the Dockerfile uses the OPEN_STOCKS_MCP_VERSION build arg
    to install the package from PyPI.
    """
    # Read Dockerfile content
    dockerfile_content = DOCKERFILE_PATH.read_text()

    # The Dockerfile should define the ARG
    assert "ARG OPEN_STOCKS_MCP_VERSION=" in dockerfile_content

    # The install command should use the variable
    # Expected: RUN pip install --no-cache-dir --upgrade open-stocks-mcp==${OPEN_STOCKS_MCP_VERSION}
    install_command = "RUN pip install --no-cache-dir --upgrade open-stocks-mcp==${OPEN_STOCKS_MCP_VERSION}"
    assert install_command in dockerfile_content, (
        "Dockerfile install command must use the pinned version: open-stocks-mcp==${OPEN_STOCKS_MCP_VERSION}"
    )

    # Ensure the unversioned command is NOT present as a standalone line
    # (We check for the line ending to avoid substring matches with the versioned command)
    unversioned_command = "RUN pip install --no-cache-dir --upgrade open-stocks-mcp"
    assert unversioned_command + "\n" not in dockerfile_content, (
        "Dockerfile contains an unversioned install command; it must be replaced with the versioned one."
    )


@pytest.mark.unit
@pytest.mark.journey_system
def test_docker_readme_no_stale_version():
    """Docker README must not contain stale package version strings."""
    readme_content = README_PATH.read_text()
    for stale in ["0.5.5", "v0.5.5"]:
        assert stale not in readme_content, (
            f"Docker README still references stale version '{stale}'"
        )


@pytest.mark.unit
@pytest.mark.journey_system
def test_docker_readme_version_matches_pyproject():
    """Docker README must reference the pinned PyPI version matching pyproject.toml."""
    with open(PYPROJECT_PATH, "rb") as f:
        pyproject_data = tomllib.load(f)
    expected_version = pyproject_data["project"]["version"]
    readme_content = README_PATH.read_text()
    assert f"open-stocks-mcp=={expected_version}" in readme_content, (
        f"Docker README must reference pinned version 'open-stocks-mcp=={expected_version}'"
    )


@pytest.mark.unit
@pytest.mark.journey_system
def test_docker_readme_tool_count_matches_app():
    """Docker README tool count must match active @mcp.tool() registrations in server/app.py."""
    app_content = APP_PY_PATH.read_text()
    actual_count = len(re.findall(r"^\s*@mcp\.tool\(\)", app_content, re.MULTILINE))
    readme_content = README_PATH.read_text()
    assert f"{actual_count} MCP tools" in readme_content, (
        f"Docker README must document active tool count ({actual_count} MCP tools); "
        "update all tool-count references in the file"
    )


@pytest.mark.unit
@pytest.mark.journey_system
def test_docker_readme_schwab_quick_start():
    """Docker README Quick Start must include optional Schwab credentials section."""
    readme_content = README_PATH.read_text()
    required_vars = [
        "SCHWAB_API_KEY",
        "SCHWAB_APP_SECRET",
        "SCHWAB_CALLBACK_URL",
        "SCHWAB_TOKEN_PATH",
        "ENABLED_BROKERS=robinhood,schwab",
    ]
    for var in required_vars:
        assert var in readme_content, (
            f"Docker README missing Schwab env var example: {var}"
        )


@pytest.mark.unit
@pytest.mark.journey_system
def test_docker_readme_schwab_tools():
    """Docker README Available Tools must list representative schwab_* tools."""
    readme_content = README_PATH.read_text()
    required_tools = [
        "schwab_account_numbers",
        "schwab_quote",
        "schwab_buy_stock_market",
        "schwab_option_chain",
        "schwab_get_dividends",
    ]
    for tool in required_tools:
        assert tool in readme_content, (
            f"Docker README Available Tools missing representative Schwab tool: {tool}"
        )
