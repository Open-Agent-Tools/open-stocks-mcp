import json
import re
from pathlib import Path

import pytest

from scripts import generate_api_docs, schwab_coverage

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


@pytest.mark.unit
@pytest.mark.journey_system
def test_tools_from_eval_file(tmp_path):
    eval_file = tmp_path / "test_schwab_eval.json"
    eval_file.write_text(
        json.dumps({
            "eval_cases": [
                {
                    "conversation": [
                        {
                            "intermediate_data": {
                                "tool_uses": [
                                    {"name": "schwab_account_numbers"},
                                    {"name": "schwab_quote"},
                                ]
                            }
                        }
                    ]
                }
            ]
        })
    )

    result = schwab_coverage.tools_from_eval_file(eval_file)

    assert result == {"schwab_account_numbers", "schwab_quote"}


@pytest.mark.unit
@pytest.mark.journey_system
def test_build_coverage_maps_tool_to_filename(tmp_path):
    eval_file = tmp_path / "test_schwab_account_test.json"
    eval_file.write_text(
        json.dumps({
            "eval_cases": [
                {
                    "conversation": [
                        {
                            "intermediate_data": {
                                "tool_uses": [{"name": "schwab_account_numbers"}]
                            }
                        }
                    ]
                }
            ]
        })
    )

    coverage = schwab_coverage.build_coverage(tmp_path)

    assert "schwab_account_numbers" in coverage
    assert eval_file.name in coverage["schwab_account_numbers"]


@pytest.mark.unit
@pytest.mark.journey_system
def test_render_coverage_markdown_checked_and_unchecked():
    tools = ["schwab_a", "schwab_b", "schwab_c"]
    tool_to_files = {"schwab_a": ["file1.json"]}

    output = schwab_coverage.render_coverage_markdown(tools, tool_to_files)

    assert "- [x] `schwab_a`" in output
    assert "- [ ] `schwab_b`" in output
    assert "- [ ] `schwab_c`" in output
    assert "1/3" in output


@pytest.mark.unit
@pytest.mark.journey_system
def test_build_coverage_live_evals_dir():
    """Verify the real evals dir returns known covered tools."""
    coverage = schwab_coverage.build_coverage()

    assert "schwab_account_numbers" in coverage
    assert "schwab_quote" in coverage
    assert "schwab_price_history" in coverage
    assert "schwab_search_instruments" in coverage
    assert "schwab_option_chain" in coverage
    assert "schwab_option_expirations" in coverage
    assert "schwab_orders" in coverage
