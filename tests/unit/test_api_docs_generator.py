import re

import pytest

from scripts import generate_api_docs


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
