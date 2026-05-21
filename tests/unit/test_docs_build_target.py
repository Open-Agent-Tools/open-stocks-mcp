import re
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.unit
@pytest.mark.journey_system
def test_generate_tool_docs_script_writes_reference(tmp_path: Path) -> None:
    output_path = tmp_path / "MCP_TOOLS_REFERENCE.md"
    repo_root = Path(__file__).resolve().parents[2]

    subprocess.run(
        [
            sys.executable,
            "scripts/generate_tool_docs.py",
            "--output",
            str(output_path),
        ],
        cwd=repo_root,
        check=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# Open Stocks MCP Tool Reference")
    match = re.search(r"^Total tools: (\d+)$", content, re.MULTILINE)
    assert match is not None
    assert int(match.group(1)) >= 79
