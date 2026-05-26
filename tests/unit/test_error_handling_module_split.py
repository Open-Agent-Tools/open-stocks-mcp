"""Regression tests for the error_handling module split."""

from open_stocks_mcp.tools import error_handling, responses
from open_stocks_mcp.tools.responses import create_success_response
from open_stocks_mcp.tools.schwab import error_handling as schwab_error_handling
from open_stocks_mcp.tools.validation import validate_symbol


def test_error_handling_reexports_core_symbols() -> None:
    assert error_handling.execute_with_retry is not None
    assert error_handling.DEFAULT_MAX_RETRIES == 3
    assert error_handling.classify_error is not None
    assert error_handling.create_error_response is not None
    assert error_handling.validate_symbol is not None


def test_schwab_error_decorator_lives_in_schwab_module() -> None:
    assert not hasattr(responses, "handle_schwab_errors")
    assert schwab_error_handling.handle_schwab_errors is not None
    assert (
        error_handling.handle_schwab_errors
        is schwab_error_handling.handle_schwab_errors
    )


def test_error_handling_does_not_export_unused_span_validator() -> None:
    assert "validate_span" not in error_handling.__all__
    assert not hasattr(error_handling, "validate_span")


def test_validation_behavior_preserved() -> None:
    assert validate_symbol("AAPL") is True
    assert validate_symbol("AAPL7") is True
    assert validate_symbol("TOO-LONG") is False


def test_success_response_default_status() -> None:
    payload = {"symbol": "AAPL"}
    response = create_success_response(payload)
    assert response["result"]["status"] == "success"
    assert response["result"]["symbol"] == "AAPL"
