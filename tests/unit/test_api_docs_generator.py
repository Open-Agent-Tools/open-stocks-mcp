import re
from pathlib import Path

import pytest

from scripts import generate_api_docs

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
@pytest.mark.journey_system
def test_generate_writes_tools_md(tmp_path):
    output_path = tmp_path / "tools.md"

    written_path = generate_api_docs.main(output_path=output_path)

    assert written_path == output_path
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")
    assert "# Open Stocks MCP — Tool Reference" in content
    assert re.search(r"\n\d+ tools registered\n", content)
    assert "### list_tools" in content
    assert "### account_info" in content


@pytest.mark.unit
@pytest.mark.journey_system
def test_committed_api_tools_doc_matches_live_registry(tmp_path):
    output_path = tmp_path / "tools.md"
    generate_api_docs.main(output_path=output_path)
    generated = output_path.read_text(encoding="utf-8")

    generated_count_match = re.search(r"\n(\d+) tools registered\n", generated)
    assert generated_count_match is not None
    generated_count = int(generated_count_match.group(1))

    committed_path = REPO_ROOT / "docs" / "api" / "tools.md"
    committed = committed_path.read_text(encoding="utf-8")
    committed_count_match = re.search(r"\n(\d+) tools registered\n", committed)
    assert committed_count_match is not None
    committed_count = int(committed_count_match.group(1))

    assert committed_count == generated_count, (
        f"Committed docs/api/tools.md has {committed_count} tools, "
        f"but live registry has {generated_count}. "
        "Run 'uv run python scripts/generate_api_docs.py'."
    )

    for tool_name in (
        "broker_comparison",
        "schwab_stream_quotes",
        "unified_watchlists",
    ):
        assert f"### {tool_name}" in committed
