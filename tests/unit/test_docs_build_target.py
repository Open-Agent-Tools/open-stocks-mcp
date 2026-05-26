import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _generate_tool_docs(tmp_path: Path) -> tuple[str, int]:
    """Run generate_tool_docs.py and return (content, tool_count)."""
    output_path = tmp_path / "MCP_TOOLS_REFERENCE.md"
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_tool_docs.py",
            "--output",
            str(output_path),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    content = output_path.read_text(encoding="utf-8")
    match = re.search(r"^Total tools: (\d+)$", content, re.MULTILINE)
    assert match is not None, "Generated docs missing 'Total tools:' line"
    return content, int(match.group(1))


@pytest.mark.unit
@pytest.mark.journey_system
def test_generate_tool_docs_script_writes_reference(tmp_path: Path) -> None:
    content, count = _generate_tool_docs(tmp_path)
    assert content.startswith("# Open Stocks MCP — Tool Reference")
    assert count >= 79


@pytest.mark.unit
@pytest.mark.journey_system
def test_committed_tool_reference_matches_live_registry(tmp_path: Path) -> None:
    _, live_count = _generate_tool_docs(tmp_path)

    committed = (REPO_ROOT / "docs" / "MCP_TOOLS_REFERENCE.md").read_text(
        encoding="utf-8"
    )
    match = re.search(r"^Total tools: (\d+)$", committed, re.MULTILINE)
    assert match is not None, "Committed MCP_TOOLS_REFERENCE.md missing 'Total tools:'"
    committed_count = int(match.group(1))

    assert committed_count == live_count, (
        f"Committed tool reference ({committed_count}) differs from live registry ({live_count}). "
        f"Run 'make docs' to regenerate."
    )


@pytest.mark.unit
@pytest.mark.journey_system
def test_prose_docs_have_no_stale_tool_counts(tmp_path: Path) -> None:
    _, live_count = _generate_tool_docs(tmp_path)

    stale_pattern = re.compile(
        r"\b\d+\s+MCP\s+tools\b|\bfor\s+all\s+\d+\s+tools\b", re.IGNORECASE
    )

    for name in ("CLAUDE.md", "README.md"):
        path = REPO_ROOT / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in stale_pattern.finditer(text):
            snippet = m.group(0)
            num = int(re.search(r"\d+", snippet).group(0))  # type: ignore[union-attr]
            if num != live_count:
                pytest.fail(
                    f"{name} contains stale tool count '{snippet}' "
                    f"(says {num}, live registry has {live_count}). "
                    f"Update the prose or reference docs/MCP_TOOLS_REFERENCE.md."
                )
