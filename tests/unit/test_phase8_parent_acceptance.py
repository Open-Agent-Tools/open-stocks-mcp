"""Parent-level acceptance tests for Phase 8 operations, docs, and configuration roadmap (#139).

Verifies that the four decomposed child slices (#163-#166) left the repository
with all artifacts discoverable from committed files.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

ROOT = Path(__file__).resolve().parents[2]


class TestReadmeDiscoverability:
    """README.md must link to all Phase 8 deliverables."""

    @pytest.fixture(autouse=True)
    def _load_readme(self) -> None:
        self.readme = (ROOT / "README.md").read_text()

    def test_links_api_docs_readme(self) -> None:
        assert "docs/api/README.md" in self.readme

    def test_links_api_tools_reference(self) -> None:
        assert "docs/api/tools.md" in self.readme

    def test_links_notebooks_via_api_docs(self) -> None:
        assert "notebook" in self.readme.lower()
        api_readme = (ROOT / "docs" / "api" / "README.md").read_text()
        assert "examples/notebooks" in api_readme

    def test_links_kubernetes_readme(self) -> None:
        assert "examples/kubernetes/README.md" in self.readme

    def test_links_config_example(self) -> None:
        assert "config.yaml.example" in self.readme

    def test_links_contributing(self) -> None:
        assert "CONTRIBUTING.md" in self.readme


class TestGeneratedToolDocs:
    """Generated tool documentation must exist with registry counts."""

    def test_api_tools_md_exists_with_count(self) -> None:
        path = ROOT / "docs" / "api" / "tools.md"
        assert path.exists(), "docs/api/tools.md missing"
        content = path.read_text()
        assert "tools registered" in content.lower() or "total tools" in content.lower()

    def test_mcp_tools_reference_exists_with_count(self) -> None:
        path = ROOT / "docs" / "MCP_TOOLS_REFERENCE.md"
        assert path.exists(), "docs/MCP_TOOLS_REFERENCE.md missing"
        content = path.read_text()
        assert "Total tools:" in content


class TestNotebookArtifacts:
    """Example notebooks must exist under examples/notebooks/."""

    EXPECTED: ClassVar[list[str]] = [
        "portfolio_snapshot.ipynb",
        "options_analysis.ipynb",
        "01_market_data_quickstart.ipynb",
        "02_trading_safe_dry_run.ipynb",
    ]

    @pytest.mark.parametrize("name", EXPECTED)
    def test_notebook_exists(self, name: str) -> None:
        path = ROOT / "examples" / "notebooks" / name
        assert path.exists(), f"examples/notebooks/{name} missing"


class TestKubernetesArtifacts:
    """Kubernetes deployment artifacts must exist under examples/kubernetes/."""

    EXPECTED: ClassVar[list[str]] = [
        "deployment.yaml",
        "service.yaml",
        "configmap.yaml",
        "persistentvolumeclaim.yaml",
        "kustomization.yaml",
        "secret.yaml.example",
        "README.md",
    ]

    @pytest.mark.parametrize("name", EXPECTED)
    def test_kubernetes_file_exists(self, name: str) -> None:
        path = ROOT / "examples" / "kubernetes" / name
        assert path.exists(), f"examples/kubernetes/{name} missing"


class TestConfigExample:
    """config.yaml.example must document feature flags including circuit breaker."""

    @pytest.fixture(autouse=True)
    def _load_config(self) -> None:
        self.content = (ROOT / "config.yaml.example").read_text()

    def test_has_feature_flags(self) -> None:
        assert "feature_flags:" in self.content

    def test_has_enable_cache(self) -> None:
        assert "enable_cache" in self.content

    def test_has_enable_circuit_breaker(self) -> None:
        assert "enable_circuit_breaker" in self.content
