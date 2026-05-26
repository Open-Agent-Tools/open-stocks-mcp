import pathlib
import tomllib

import pytest

# Paths relative to the project root
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
DOCKERFILE_PATH = PROJECT_ROOT / "examples" / "open-stocks-mcp-docker" / "Dockerfile"


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
