"""Schwab-specific error handling helpers."""

import functools
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar

from open_stocks_mcp.tools.exceptions import classify_schwab_error
from open_stocks_mcp.tools.responses import create_error_response

P = ParamSpec("P")
R = TypeVar("R")


def handle_schwab_errors(
    func: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R | dict[str, Any]]]:
    """Decorator to handle Schwab API errors consistently."""

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | dict[str, Any]:
        context = f"in {func.__name__}"
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return create_error_response(classify_schwab_error(e), context)

    return wrapper
