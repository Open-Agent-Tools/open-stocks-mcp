"""Compatibility facade for split Robinhood account feature tools."""

from open_stocks_mcp.tools.robinhood_account_feature_summary_tools import (
    get_account_features,
)
from open_stocks_mcp.tools.robinhood_margin_tools import (
    get_margin_calls,
    get_margin_interest,
)
from open_stocks_mcp.tools.robinhood_notification_tools import (
    get_latest_notification,
    get_notifications,
)
from open_stocks_mcp.tools.robinhood_referral_tools import get_referrals
from open_stocks_mcp.tools.robinhood_subscription_tools import get_subscription_fees

__all__ = [
    "get_account_features",
    "get_latest_notification",
    "get_margin_calls",
    "get_margin_interest",
    "get_notifications",
    "get_referrals",
    "get_subscription_fees",
]
