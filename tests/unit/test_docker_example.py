import pathlib
import re
import tomllib

import pytest

# Paths relative to the project root
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
DOCKERFILE_PATH = PROJECT_ROOT / "examples" / "open-stocks-mcp-docker" / "Dockerfile"
DOCKER_README_PATH = PROJECT_ROOT / "examples" / "open-stocks-mcp-docker" / "README.md"
APP_PY_PATH = PROJECT_ROOT / "src" / "open_stocks_mcp" / "server" / "app.py"

_STALE_VERSION_PATTERN = re.compile(r"0\.5\.5")

_REQUIRED_SCHWAB_ENV_VARS = [
    "SCHWAB_API_KEY",
    "SCHWAB_APP_SECRET",
    "SCHWAB_CALLBACK_URL",
    "SCHWAB_TOKEN_PATH",
    "ENABLED_BROKERS=robinhood,schwab",
]

_REQUIRED_SCHWAB_TOOLS = [
    "schwab_account_numbers",
    "schwab_quote",
    "schwab_buy_stock_market",
    "schwab_option_chain",
    "schwab_get_dividends",
]


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
    """Docker README must not reference the stale 0.5.5 release."""
    readme_content = DOCKER_README_PATH.read_text()
    matches = _STALE_VERSION_PATTERN.findall(readme_content)
    assert not matches, (
        f"Docker README still contains stale version string '0.5.5' ({len(matches)} occurrences). "
        "Update every reference to match pyproject.toml."
    )


@pytest.mark.unit
@pytest.mark.journey_system
def test_docker_readme_tool_count_matches_app():
    """Docker README tool count must match the @mcp.tool() registrations in server/app.py."""
    readme_content = DOCKER_README_PATH.read_text()
    app_content = APP_PY_PATH.read_text()

    actual_count = sum(
        1
        for line in app_content.splitlines()
        if line.strip() == "@mcp.tool()"
    )

    # Find all numeric tool-count claims in the README (e.g. "152 MCP tools", "**152 MCP tools**")
    claimed = re.findall(r"\b(\d+)\s+MCP tools\b", readme_content)
    assert claimed, "Docker README contains no '\\d+ MCP tools' claim — add the tool count."

    wrong = [c for c in claimed if int(c) != actual_count]
    assert not wrong, (
        f"Docker README claims {wrong} MCP tools but src/open_stocks_mcp/server/app.py "
        f"has {actual_count} @mcp.tool() registrations. Update every count in the README."
    )


@pytest.mark.unit
@pytest.mark.journey_system
def test_docker_readme_includes_schwab_env_vars():
    """Docker README Quick Start must document optional Schwab environment variables."""
    readme_content = DOCKER_README_PATH.read_text()
    missing = [var for var in _REQUIRED_SCHWAB_ENV_VARS if var not in readme_content]
    assert not missing, (
        f"Docker README Quick Start is missing Schwab env vars: {missing}. "
        "Add an optional Schwab credentials block to the Quick Start section."
    )


@pytest.mark.unit
@pytest.mark.journey_system
def test_docker_readme_lists_schwab_tools():
    """Docker README Available Tools section must include representative schwab_* tools."""
    readme_content = DOCKER_README_PATH.read_text()
    missing = [tool for tool in _REQUIRED_SCHWAB_TOOLS if tool not in readme_content]
    assert not missing, (
        f"Docker README Available Tools section is missing schwab_* tools: {missing}. "
        "Add representative Schwab tools to the Available Tools listing."
    )


@pytest.mark.unit
@pytest.mark.journey_system
def test_docker_readme_documents_pypi_pin_policy():
    """Docker README must explain the pinned PyPI version policy via OPEN_STOCKS_MCP_VERSION."""
    readme_content = DOCKER_README_PATH.read_text()
    assert "OPEN_STOCKS_MCP_VERSION" in readme_content, (
        "Docker README must document the OPEN_STOCKS_MCP_VERSION build arg used to pin the "
        "PyPI package version. Add a note explaining that changing the release requires "
        "updating this build arg before rebuilding."
    )
