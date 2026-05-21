.PHONY: help docs

help:
	@echo "Available targets:"
	@echo "  docs  Generate docs/MCP_TOOLS_REFERENCE.md from live MCP tools"

docs:
	uv run python scripts/generate_tool_docs.py --output docs/MCP_TOOLS_REFERENCE.md
