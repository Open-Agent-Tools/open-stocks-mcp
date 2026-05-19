"""Validation helpers for tool parameters."""


def validate_symbol(symbol: str) -> bool:
    """Validate a stock symbol format."""
    if not symbol or not isinstance(symbol, str):
        return False

    normalized = symbol.strip().upper()
    if len(normalized) < 1 or len(normalized) > 5:
        return False

    return normalized.isalnum()


def validate_period(period: str) -> bool:
    """Validate a time period parameter."""
    valid_periods = ["day", "week", "month", "3month", "year", "5year", "all"]
    return period in valid_periods


def validate_span(span: str) -> bool:
    """Validate a time span parameter."""
    valid_spans = ["day", "week", "month", "3month", "year", "5year", "all"]
    return span in valid_spans
