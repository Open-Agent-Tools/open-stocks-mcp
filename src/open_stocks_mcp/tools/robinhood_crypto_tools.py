"""MCP tools for Robin Stocks cryptocurrency operations.

Crypto trading via robin-stocks is not yet implemented. These stubs exist as
placeholders; none are registered in the MCP server until implemented.
"""

from typing import Any


async def get_crypto_positions() -> dict[str, Any]:
    """Get current cryptocurrency positions (not yet implemented)."""
    raise NotImplementedError(
        "Crypto positions are not yet implemented. "
        "This function is not registered as an MCP tool."
    )
