# Trading Test Safety Guidelines

## ⚠️ CRITICAL SAFETY NOTICE ⚠️

**NEVER create automated tests that place real trading orders or cancel live orders.**

## Prohibited Test Types

### ❌ DO NOT CREATE TESTS FOR:
- `order_buy_market()` - Places real market buy orders
- `order_sell_market()` - Places real market sell orders  
- `order_buy_limit()` - Places real limit buy orders
- `order_sell_limit()` - Places real limit sell orders
- `order_buy_stop_loss()` - Places real stop loss buy orders
- `order_sell_stop_loss()` - Places real stop loss sell orders
- `order_buy_trailing_stop()` - Places real trailing stop buy orders
- `order_sell_trailing_stop()` - Places real trailing stop sell orders
- `order_buy_fractional_by_price()` - Places real fractional share orders
- `order_buy_option_limit()` - Places real option buy orders
- `order_sell_option_limit()` - Places real option sell orders
- `order_option_credit_spread()` - Places real credit spread orders
- `order_option_debit_spread()` - Places real debit spread orders
- `cancel_stock_order()` - Cancels real stock orders
- `cancel_option_order()` - Cancels real option orders
- `cancel_all_stock_orders()` - Cancels all real stock orders
- `cancel_all_option_orders()` - Cancels all real option orders

## ✅ SAFE TESTING APPROACHES

### 1. Mock Testing Only
```python
from unittest.mock import patch, MagicMock
import pytest

@patch('robin_stocks.robinhood.order_buy_market')
async def test_order_buy_market_validation(mock_order):
    """Test validation logic without placing real orders"""
    mock_order.return_value = {"id": "test_order_id", "state": "confirmed"}
    
    # Test only validation and response formatting
    result = await order_buy_market("AAPL", 1)
    assert result["result"]["status"] == "success"
    mock_order.assert_called_once_with("AAPL", 1)
```

### 2. Input Validation Testing
```python
async def test_order_buy_market_invalid_inputs():
    """Test input validation without API calls"""
    # Test invalid symbol
    result = await order_buy_market("", 1)
    assert "error" in result["result"]
    
    # Test invalid quantity
    result = await order_buy_market("AAPL", -1)
    assert "error" in result["result"]
```

### 3. Error Handling Testing
```python
@patch('robin_stocks.robinhood.order_buy_market')
async def test_order_buy_market_api_error(mock_order):
    """Test error handling without real orders"""
    mock_order.side_effect = Exception("API Error")
    
    result = await order_buy_market("AAPL", 1)
    assert result["result"]["status"] == "error"
```

## ✅ ALLOWED READ-ONLY TESTS

These are safe because they only retrieve data:
- `get_stock_orders()` - Retrieves historical orders
- `get_options_orders()` - Retrieves historical options orders  
- `get_all_open_stock_orders()` - Lists current open orders
- `get_all_open_option_orders()` - Lists current open option orders

## Test Markers for Safety

Always mark any trading-related tests appropriately:

```python
@pytest.mark.integration  # Requires credentials
@pytest.mark.live_market  # Requires live market data
@pytest.mark.exception_test  # Error handling tests
@pytest.mark.slow  # Performance tests
```

## Safe Test Execution

### Development Testing (Recommended)
```bash
pytest -m "not slow and not exception_test and not integration"
```

### Skip All Integration Tests
```bash
pytest -m "not integration"
```

### Skip Exception Tests (Default)
```bash
pytest -m "not exception_test"
```

## Manual Testing Only

Trading functionality should only be tested manually:

1. **Local Development Server**: Use `uv run open-stocks-mcp-server --transport http --port 3001`
2. **Small Test Orders**: Place minimal orders with small amounts
3. **Paper Trading**: Use a test account if available
4. **Immediate Cancellation**: Cancel test orders immediately after placement

## Violation Consequences

Creating tests that place real orders could result in:
- ❌ Unintended financial losses
- ❌ Accidental portfolio changes
- ❌ Regulatory violations
- ❌ Account suspension

## Review Checklist

Before committing any trading-related tests:

- [ ] Does the test call any `order_*` functions?
- [ ] Does the test call any `cancel_*` functions?
- [ ] Are all API calls properly mocked?
- [ ] Does the test only validate inputs and outputs?
- [ ] Is the test marked with appropriate markers?
- [ ] Will this test work in CI/CD without credentials?

**Remember: When in doubt, don't create the test. Trading functionality should be tested manually only.**