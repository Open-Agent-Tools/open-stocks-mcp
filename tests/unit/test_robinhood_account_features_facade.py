"""Regression tests for legacy robinhood account features facade."""

from open_stocks_mcp.tools import robinhood_account_features_tools as facade


def test_facade_reexports_public_functions() -> None:
    """Legacy facade should continue exposing the seven public callables."""
    names = [
        "get_notifications",
        "get_latest_notification",
        "get_margin_calls",
        "get_margin_interest",
        "get_subscription_fees",
        "get_referrals",
        "get_account_features",
    ]

    for name in names:
        assert hasattr(facade, name)
        assert callable(getattr(facade, name))
