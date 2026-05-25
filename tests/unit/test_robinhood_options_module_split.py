"""Compatibility tests for split Robinhood options modules."""

from open_stocks_mcp.tools.options.chains import (
    find_tradable_options,
    get_options_chains,
)
from open_stocks_mcp.tools.options.market_data import (
    get_option_historicals,
    get_option_market_data,
)
from open_stocks_mcp.tools.options.positions import (
    get_aggregate_positions,
    get_all_option_positions,
    get_open_option_positions,
    get_open_option_positions_with_details,
)
from open_stocks_mcp.tools.robinhood_options_tools import (
    find_tradable_options as legacy_find_tradable_options,
)
from open_stocks_mcp.tools.robinhood_options_tools import (
    get_aggregate_positions as legacy_get_aggregate_positions,
)
from open_stocks_mcp.tools.robinhood_options_tools import (
    get_all_option_positions as legacy_get_all_option_positions,
)
from open_stocks_mcp.tools.robinhood_options_tools import (
    get_open_option_positions as legacy_get_open_option_positions,
)
from open_stocks_mcp.tools.robinhood_options_tools import (
    get_open_option_positions_with_details as legacy_get_open_option_positions_with_details,
)
from open_stocks_mcp.tools.robinhood_options_tools import (
    get_option_historicals as legacy_get_option_historicals,
)
from open_stocks_mcp.tools.robinhood_options_tools import (
    get_option_market_data as legacy_get_option_market_data,
)
from open_stocks_mcp.tools.robinhood_options_tools import (
    get_options_chains as legacy_get_options_chains,
)


def test_reexports_chain_functions() -> None:
    assert legacy_get_options_chains is get_options_chains
    assert legacy_find_tradable_options is find_tradable_options


def test_reexports_market_data_functions() -> None:
    assert legacy_get_option_market_data is get_option_market_data
    assert legacy_get_option_historicals is get_option_historicals


def test_reexports_positions_functions() -> None:
    assert legacy_get_aggregate_positions is get_aggregate_positions
    assert legacy_get_all_option_positions is get_all_option_positions
    assert legacy_get_open_option_positions is get_open_option_positions
    assert (
        legacy_get_open_option_positions_with_details
        is get_open_option_positions_with_details
    )
