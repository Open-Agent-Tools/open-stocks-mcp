# Schwab-py Integration Plan

**Project**: Open Stocks MCP Multi-Broker Support
**Target**: Add Charles Schwab account support via schwab-py library
**Current State**: v0.6.4 with Robinhood-only support (80 active MCP tools)

---

## Executive Summary

This plan outlines the architecture and implementation strategy for adding Charles Schwab support to the Open Stocks MCP server while maintaining backward compatibility with existing Robinhood functionality. The design follows a broker-agnostic abstraction pattern that will support multiple brokers simultaneously.

---

## Research Findings

### Schwab-py Library Analysis

**Key Characteristics:**
- **Authentication**: OAuth-based (vs Robinhood's username/password)
- **API Pattern**: Synchronous (matches robin-stocks)
- **Philosophy**: Minimal wrapping, returns raw API responses
- **Setup**: Requires Schwab developer account, API key, app secret, callback URL
- **Approval Time**: Several days for API access approval

**Capabilities:**
- Market data (quotes, fundamentals, historical prices)
- Options chains and market data
- Trading (orders, execution, management)
- Account information
- Streaming quotes (real-time)

**Limitations:**
- No paper trading support
- No historical options pricing
- Not affiliated with ThinkorSwim
- Requires manual developer approval

**API Comparison with Robinhood:**

| Feature | Robinhood (robin-stocks) | Schwab (schwab-py) |
|---------|-------------------------|-------------------|
| Authentication | Username/Password + Pickle | OAuth + Token Refresh |
| API Style | Synchronous | Synchronous |
| Market Data | ✅ Full | ✅ Full |
| Options | ✅ Full | ✅ Full |
| Trading | ✅ Full | ✅ Full |
| Streaming | ❌ Limited | ✅ Full |
| Crypto | ✅ Supported | ❌ Not Supported |
| Paper Trading | ❌ No | ❌ No |

---

## Current Architecture Analysis

### Existing Robinhood Integration

**File Structure:**
```
src/open_stocks_mcp/
├── server/
│   ├── app.py                      # MCP server initialization, tool registration
│   └── http_transport.py           # HTTP/SSE transport layer
├── tools/
│   ├── robinhood_account_tools.py           # 4 tools
│   ├── robinhood_account_features_tools.py  # 7 tools
│   ├── robinhood_advanced_portfolio_tools.py # 3 tools
│   ├── robinhood_crypto_tools.py            # 3 tools (Schwab won't support)
│   ├── robinhood_dividend_tools.py          # 5 tools
│   ├── robinhood_market_data_tools.py       # 9 tools
│   ├── robinhood_options_tools.py           # 8 tools
│   ├── robinhood_order_tools.py             # 2 tools
│   ├── robinhood_stock_tools.py             # 9 tools
│   ├── robinhood_trading_tools.py           # 15 tools
│   ├── robinhood_user_profile_tools.py      # 7 tools
│   ├── robinhood_watchlist_tools.py         # 5 tools
│   ├── robinhood_tools.py                   # Utility (list_available_tools)
│   ├── session_manager.py                   # Robinhood-specific auth
│   ├── rate_limiter.py                      # Broker-agnostic (reusable)
│   └── error_handling.py                    # Broker-agnostic (reusable)
├── config.py                       # Configuration management
├── logging_config.py               # Logging setup
└── monitoring.py                   # Metrics collection
```

**Key Patterns:**
1. **Tool Organization**: 13 category-specific files (81 total async functions)
2. **Error Handling**: Centralized decorator pattern (`@handle_robin_stocks_errors`)
3. **Retry Logic**: `execute_with_retry()` with exponential backoff
4. **Session Management**: `SessionManager` class handles auth lifecycle
5. **Rate Limiting**: Token bucket algorithm via `RateLimiter`
6. **Response Format**: All tools return `{"result": {...}}`

**Current Limitations:**
- Hardcoded to Robinhood API
- Session manager tightly coupled to robin-stocks
- Tool names don't indicate broker (e.g., `get_portfolio` vs `robinhood_get_portfolio`)
- No broker selection mechanism

---

## Proposed Architecture

### 1. Broker Abstraction Layer

Create a clean abstraction that allows tools to work across brokers:

```python
# src/open_stocks_mcp/brokers/base.py
from abc import ABC, abstractmethod
from typing import Any

class BaseBroker(ABC):
    """Abstract base class for broker integrations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Broker name (e.g., 'robinhood', 'schwab')"""
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with broker API"""
        pass

    @abstractmethod
    async def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        pass

    @abstractmethod
    async def logout(self) -> None:
        """Logout and clear session"""
        pass

    # Account operations
    @abstractmethod
    async def get_account_info(self) -> dict[str, Any]:
        """Get account information"""
        pass

    @abstractmethod
    async def get_portfolio(self) -> dict[str, Any]:
        """Get portfolio holdings"""
        pass

    # Market data operations
    @abstractmethod
    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Get stock quote by symbol"""
        pass

    @abstractmethod
    async def get_stock_price(self, symbol: str) -> dict[str, Any]:
        """Get current stock price"""
        pass

    # Trading operations
    @abstractmethod
    async def order_buy_market(
        self, symbol: str, quantity: float
    ) -> dict[str, Any]:
        """Place market buy order"""
        pass

    # ... additional abstract methods for all common operations
```

### 2. Broker Implementations

#### Robinhood Adapter
```python
# src/open_stocks_mcp/brokers/robinhood.py
import robin_stocks.robinhood as rh
from open_stocks_mcp.brokers.base import BaseBroker
from open_stocks_mcp.tools.error_handling import execute_with_retry

class RobinhoodBroker(BaseBroker):
    """Robinhood broker implementation."""

    def __init__(self):
        self.session_manager = None  # Migrate from tools/session_manager.py

    @property
    def name(self) -> str:
        return "robinhood"

    async def authenticate(self) -> bool:
        """Use existing SessionManager logic"""
        # Migrate existing authentication code
        pass

    async def get_portfolio(self) -> dict[str, Any]:
        """Wraps existing robinhood_account_tools.get_portfolio"""
        result = await execute_with_retry(rh.profiles.load_portfolio_profile)
        return {"result": result}

    # ... implement all abstract methods using existing tool code
```

#### Schwab Adapter
```python
# src/open_stocks_mcp/brokers/schwab.py
from schwab import auth, client
from open_stocks_mcp.brokers.base import BaseBroker

class SchwabBroker(BaseBroker):
    """Charles Schwab broker implementation."""

    def __init__(self, api_key: str, app_secret: str, callback_url: str, token_path: str):
        self.api_key = api_key
        self.app_secret = app_secret
        self.callback_url = callback_url
        self.token_path = token_path
        self.client = None

    @property
    def name(self) -> str:
        return "schwab"

    async def authenticate(self) -> bool:
        """OAuth authentication via schwab-py"""
        try:
            self.client = auth.easy_client(
                self.api_key,
                self.app_secret,
                self.callback_url,
                self.token_path
            )
            return True
        except Exception as e:
            logger.error(f"Schwab authentication failed: {e}")
            return False

    async def get_portfolio(self) -> dict[str, Any]:
        """Get Schwab portfolio via API"""
        # Map schwab-py API to common format
        # Response format will differ from Robinhood
        pass

    # ... implement all abstract methods
```

### 3. Broker Registry

```python
# src/open_stocks_mcp/brokers/registry.py
from typing import Dict
from open_stocks_mcp.brokers.base import BaseBroker

class BrokerRegistry:
    """Manages available broker instances."""

    def __init__(self):
        self._brokers: Dict[str, BaseBroker] = {}
        self._active_broker: str | None = None

    def register(self, broker: BaseBroker) -> None:
        """Register a broker instance"""
        self._brokers[broker.name] = broker
        if self._active_broker is None:
            self._active_broker = broker.name

    def get_broker(self, name: str | None = None) -> BaseBroker:
        """Get broker by name, or active broker if name is None"""
        broker_name = name or self._active_broker
        if not broker_name or broker_name not in self._brokers:
            raise ValueError(f"Broker not found: {broker_name}")
        return self._brokers[broker_name]

    def set_active_broker(self, name: str) -> None:
        """Set the active broker"""
        if name not in self._brokers:
            raise ValueError(f"Broker not registered: {name}")
        self._active_broker = name

    def list_brokers(self) -> list[str]:
        """List all registered brokers"""
        return list(self._brokers.keys())

    async def authenticate_all(self) -> dict[str, bool]:
        """Authenticate all registered brokers"""
        results = {}
        for name, broker in self._brokers.items():
            results[name] = await broker.authenticate()
        return results

# Global registry instance
_registry: BrokerRegistry | None = None

def get_broker_registry() -> BrokerRegistry:
    """Get or create the global broker registry"""
    global _registry
    if _registry is None:
        _registry = BrokerRegistry()
    return _registry
```

### 4. Tool Registration Strategy

**Option A: Broker-Prefixed Tools (Recommended)**
```python
# Tools are registered with broker prefix
@mcp.tool()
async def robinhood_get_portfolio() -> dict[str, Any]:
    """Get Robinhood portfolio"""
    broker = get_broker_registry().get_broker("robinhood")
    return await broker.get_portfolio()

@mcp.tool()
async def schwab_get_portfolio() -> dict[str, Any]:
    """Get Schwab portfolio"""
    broker = get_broker_registry().get_broker("schwab")
    return await broker.get_portfolio()
```

**Advantages:**
- Clear broker identification
- No ambiguity for LLMs
- Easy to discover available brokers
- Backward compatible (add schwab_ tools without changing robinhood_ tools)

**Option B: Unified Tools with Broker Parameter**
```python
@mcp.tool()
async def get_portfolio(broker: str = "robinhood") -> dict[str, Any]:
    """Get portfolio from specified broker"""
    b = get_broker_registry().get_broker(broker)
    return await b.get_portfolio()
```

**Advantages:**
- Fewer total tools
- Simpler for users who only use one broker

**Disadvantages:**
- Requires broker parameter on every call
- Less discoverable
- Breaks backward compatibility

**Recommendation**: Use **Option A** (broker-prefixed tools) for clarity and backward compatibility.

### 5. Configuration Strategy

```python
# src/open_stocks_mcp/config.py (updated)
from pydantic import BaseModel

class RobinhoodConfig(BaseModel):
    """Robinhood-specific configuration"""
    username: str
    password: str
    pickle_name: str = "robinhood"
    session_timeout_hours: int = 23

class SchwabConfig(BaseModel):
    """Schwab-specific configuration"""
    api_key: str
    app_secret: str
    callback_url: str = "https://127.0.0.1:8182/"
    token_path: str = "~/.tokens/schwab_token.json"

class BrokerSettings(BaseModel):
    """Multi-broker configuration"""
    enabled_brokers: list[str] = ["robinhood"]  # Default to Robinhood only
    default_broker: str = "robinhood"
    robinhood: RobinhoodConfig | None = None
    schwab: SchwabConfig | None = None

class ServerConfig(BaseModel):
    """Server configuration (existing, extended)"""
    brokers: BrokerSettings
    # ... existing fields
```

**Environment Variables:**
```bash
# Robinhood (existing)
ROBINHOOD_USERNAME=user@example.com
ROBINHOOD_PASSWORD=password

# Schwab (new)
SCHWAB_API_KEY=your_api_key
SCHWAB_APP_SECRET=your_app_secret
SCHWAB_CALLBACK_URL=https://127.0.0.1:8182/
SCHWAB_TOKEN_PATH=~/.tokens/schwab_token.json

# Multi-broker settings
ENABLED_BROKERS=robinhood,schwab
DEFAULT_BROKER=robinhood
```

---

## Implementation Phases

### Phase 1: Abstraction Layer Foundation
**Dependencies**: None
**Estimated Complexity**: Medium

**Tasks**:
1. Create `src/open_stocks_mcp/brokers/` directory
2. Implement `base.py` with `BaseBroker` abstract class
3. Define all abstract methods matching current tool capabilities
4. Create `registry.py` with `BrokerRegistry`
5. Add broker configuration models to `config.py`
6. Write unit tests for broker registry

**Deliverables**:
- `brokers/base.py` - Abstract broker interface
- `brokers/registry.py` - Broker management
- Updated `config.py` - Multi-broker config support
- Unit tests for registry

**Success Criteria**:
- Registry can register/retrieve brokers
- Config supports multiple broker types
- All tests pass

---

### Phase 2: Robinhood Adapter Migration
**Dependencies**: Phase 1
**Estimated Complexity**: High

**Tasks**:
1. Create `brokers/robinhood.py` implementing `BaseBroker`
2. Migrate `SessionManager` into `RobinhoodBroker` class
3. Refactor existing tool code to use broker adapter
4. Keep existing tool names (no breaking changes yet)
5. Update `server/app.py` to use registry
6. Ensure all 80 existing tools still work via adapter

**Deliverables**:
- `brokers/robinhood.py` - Full Robinhood implementation
- Migrated session management
- Updated server initialization
- All existing tests passing

**Success Criteria**:
- All 80 Robinhood tools work through adapter
- No breaking changes to existing API
- Authentication still works
- All journey tests pass

---

### Phase 3: Schwab Adapter Implementation
**Dependencies**: Phase 2
**Estimated Complexity**: High

**Tasks**:
1. Add `schwab-py` to dependencies in `pyproject.toml`
2. Create `brokers/schwab.py` implementing `BaseBroker`
3. Implement OAuth authentication flow
4. Map Schwab API responses to common format
5. Implement core operations (account, market data, trading)
6. Handle Schwab-specific differences (no crypto support, etc.)
7. Add Schwab configuration to environment setup

**Deliverables**:
- `brokers/schwab.py` - Full Schwab implementation
- OAuth token management
- Schwab API integration
- Configuration documentation

**Success Criteria**:
- Schwab authentication works (OAuth flow)
- Core operations return data in expected format
- Error handling works correctly
- Tokens refresh automatically

---

### Phase 4: Dual Tool Registration
**Dependencies**: Phase 3
**Estimated Complexity**: Medium

**Tasks**:
1. Create `tools/broker_tools.py` with broker-prefixed tools
2. Register both `robinhood_*` and `schwab_*` tool sets
3. Update tool descriptions to indicate broker
4. Add broker switching utilities (`set_active_broker`, `list_brokers`)
5. Update `/tools` endpoint to show broker groupings
6. Create migration guide for users

**Deliverables**:
- Broker-prefixed tools (e.g., `schwab_get_portfolio`)
- Tool documentation updates
- Migration guide
- Updated API documentation

**Success Criteria**:
- Both broker tool sets registered
- LLM can discover and call Schwab tools
- Backward compatibility maintained
- Clear tool naming convention

---

### Phase 5: Testing & Documentation
**Dependencies**: Phase 4
**Estimated Complexity**: Medium

**Tasks**:
1. Create journey tests for Schwab tools
2. Add integration tests for multi-broker scenarios
3. Update `CLAUDE.md` with Schwab setup instructions
4. Create `docs/SCHWAB_SETUP.md` guide
5. Update README with multi-broker examples
6. Add ADK evaluations for Schwab tools
7. Create Docker example with both brokers

**Deliverables**:
- Schwab journey tests (11 categories)
- Multi-broker integration tests
- Complete documentation
- ADK evaluations
- Docker example

**Success Criteria**:
- Test coverage ≥80% for Schwab code
- All journey categories have tests
- Documentation complete and accurate
- Docker example works out of box

---

### Phase 6: Enhanced Features (Future)
**Dependencies**: Phase 5
**Estimated Complexity**: Low-Medium

**Tasks**:
1. Add Schwab streaming quotes support
2. Implement cross-broker portfolio aggregation
3. Add broker comparison tools
4. Create unified watchlist across brokers
5. Support concurrent broker operations
6. Add broker health monitoring

**Deliverables**:
- Streaming quote support
- Portfolio aggregation tools
- Cross-broker features
- Enhanced monitoring

**Success Criteria**:
- Streaming works reliably
- Can aggregate data from both brokers
- Health checks work for all brokers

---

## Migration Strategy

### Backward Compatibility

**Guarantee**: Existing Robinhood-only users see zero breaking changes

**Approach**:
1. Keep all existing tool names unchanged
2. Add new Schwab tools alongside (don't replace)
3. Default broker remains Robinhood
4. Existing environment variables work as-is
5. If no Schwab config provided, server works exactly as v0.6.4

### User Migration Path

**Robinhood-only users (no action required)**:
- Continue using existing setup
- No configuration changes needed
- All tools work identically

**Users adding Schwab**:
1. Create Schwab developer account
2. Get API approval (several days)
3. Add Schwab env vars to `.env`
4. Set `ENABLED_BROKERS=robinhood,schwab`
5. Restart server
6. Access Schwab tools with `schwab_*` prefix

**Users switching to Schwab-only**:
1. Complete Schwab setup
2. Set `ENABLED_BROKERS=schwab`
3. Set `DEFAULT_BROKER=schwab`
4. Use `schwab_*` prefixed tools

---

## Technical Considerations

### Authentication Differences

| Aspect | Robinhood | Schwab |
|--------|-----------|--------|
| Method | Username/Password | OAuth 2.0 |
| Storage | Pickle file | JSON token file |
| Refresh | Session re-login | Automatic token refresh |
| MFA | Sometimes required | Required for setup |
| Timeout | 23 hours | Token-based (varies) |

### API Response Mapping

**Challenge**: Schwab and Robinhood APIs return different formats

**Solution**: Normalize responses in broker adapter

```python
# Example: Portfolio response normalization
class RobinhoodBroker(BaseBroker):
    async def get_portfolio(self) -> dict[str, Any]:
        raw = await execute_with_retry(rh.profiles.load_portfolio_profile)
        return {
            "result": {
                "market_value": raw.get("market_value"),
                "total_return": raw.get("total_return_today"),
                # ... standardized fields
            }
        }

class SchwabBroker(BaseBroker):
    async def get_portfolio(self) -> dict[str, Any]:
        raw = await self.client.get_account(...)
        # Map Schwab response to same format
        return {
            "result": {
                "market_value": raw["securitiesAccount"]["currentBalances"]["liquidationValue"],
                "total_return": ...,  # Calculate from Schwab data
                # ... standardized fields
            }
        }
```

### Rate Limiting

**Current**: Single `RateLimiter` instance (broker-agnostic)

**Enhancement**: Per-broker rate limiters

```python
class BrokerRegistry:
    def __init__(self):
        self._brokers: Dict[str, BaseBroker] = {}
        self._rate_limiters: Dict[str, RateLimiter] = {}

    def get_rate_limiter(self, broker_name: str) -> RateLimiter:
        """Get rate limiter for specific broker"""
        if broker_name not in self._rate_limiters:
            # Different limits for different brokers
            limits = {
                "robinhood": {"requests_per_minute": 30},
                "schwab": {"requests_per_minute": 120},  # Schwab allows more
            }
            self._rate_limiters[broker_name] = RateLimiter(**limits[broker_name])
        return self._rate_limiters[broker_name]
```

### Error Handling

**Current**: `RobinStocksError` hierarchy

**Enhancement**: Broker-agnostic errors

```python
# src/open_stocks_mcp/tools/error_handling.py (refactor)
class BrokerError(Exception):
    """Base exception for broker operations"""
    def __init__(self, message: str, broker: str, error_type: str):
        self.broker = broker
        self.error_type = error_type
        super().__init__(f"[{broker}] {message}")

class BrokerAuthenticationError(BrokerError):
    """Authentication failed for broker"""
    def __init__(self, broker: str, message: str):
        super().__init__(message, broker, "authentication")
```

### Testing Strategy

**Unit Tests**:
- Mock broker APIs (don't hit real endpoints)
- Test each adapter independently
- Verify response normalization

**Integration Tests**:
- Use live credentials (marked as `@pytest.mark.integration`)
- Test against real APIs
- Separate markers: `@pytest.mark.robinhood`, `@pytest.mark.schwab`

**Journey Tests**:
- Extend existing 11 categories to both brokers
- Use markers: `@pytest.mark.journey_account`, `@pytest.mark.schwab`
- Example: `test_schwab_account_info` vs `test_robinhood_account_info`

---

## Risk Assessment

### High Risk Items

1. **Schwab API Approval Delays**
   - Risk: Can take days/weeks to get API access
   - Mitigation: Start approval process early, use mock responses for development

2. **OAuth Complexity**
   - Risk: OAuth flow more complex than username/password
   - Mitigation: Use `schwab-py`'s `easy_client()`, extensive testing

3. **Breaking Changes to Existing Tools**
   - Risk: Refactoring could break Robinhood functionality
   - Mitigation: Comprehensive test suite, backward compatibility guarantee

### Medium Risk Items

1. **API Response Differences**
   - Risk: Schwab responses may not map cleanly to Robinhood format
   - Mitigation: Flexible normalization layer, document differences

2. **Performance Impact**
   - Risk: Abstraction layer could slow down calls
   - Mitigation: Minimal wrapping, async throughout, benchmarking

3. **Token Management**
   - Risk: OAuth tokens more complex than pickle files
   - Mitigation: Leverage `schwab-py` token handling, persistent storage

### Low Risk Items

1. **Configuration Complexity**
   - Risk: More config options could confuse users
   - Mitigation: Good defaults, clear documentation, examples

2. **Test Suite Size**
   - Risk: Doubling tests for two brokers
   - Mitigation: Shared test fixtures, parameterized tests

---

## Success Metrics

### Technical Metrics
- ✅ All 80 existing Robinhood tools still work
- ✅ Zero breaking changes to v0.6.4 API
- ✅ Schwab tools match Robinhood tool count (minus crypto)
- ✅ Test coverage ≥80% for new broker code
- ✅ MyPy type checking: 0 errors
- ✅ Ruff linting: All checks pass

### Functional Metrics
- ✅ OAuth authentication flow works reliably
- ✅ Token refresh happens automatically
- ✅ Both brokers can be used simultaneously
- ✅ Rate limiting works per-broker
- ✅ Error handling provides clear broker context

### User Experience Metrics
- ✅ Clear setup documentation (≤10 steps)
- ✅ Docker example works out of box
- ✅ Migration guide available
- ✅ LLM can discover and use both broker sets
- ✅ Tool descriptions clearly indicate broker

---

## Open Questions

1. **Naming Convention**: Confirm `schwab_get_portfolio` vs `get_schwab_portfolio`
   - **Recommendation**: `schwab_get_portfolio` (matches verb-first pattern)

2. **Multi-Account Support**: Should we support multiple accounts per broker?
   - **Recommendation**: Phase 7+ feature, not initial release

3. **Cross-Broker Operations**: Should portfolio tools aggregate both brokers?
   - **Recommendation**: Add as Phase 6 feature, keep separate initially

4. **Deprecation Path**: Should old non-prefixed tools eventually be deprecated?
   - **Recommendation**: No, maintain backward compatibility indefinitely

5. **Streaming Support**: How to handle Schwab streaming quotes?
   - **Recommendation**: Phase 6 feature, use SSE endpoint

---

## Next Steps

1. **Review & Approval**: Get feedback on this plan
2. **Schwab API Signup**: Create developer account, start approval process
3. **Phase 1 Implementation**: Start with abstraction layer
4. **Prototype**: Build minimal Schwab adapter to validate approach
5. **Iterate**: Refine based on learnings from prototype

---

## Appendix A: Tool Mapping

### Tools Available in Both Brokers (≈70 tools)

**Account Operations**:
- `get_account_info`
- `get_portfolio`
- `get_positions`
- `get_account_details`

**Market Data**:
- `get_stock_quote`
- `get_stock_price`
- `get_stock_earnings`
- `get_stock_news`
- `get_options_chains`

**Trading**:
- `order_buy_market`
- `order_sell_market`
- `order_buy_limit`
- `order_sell_limit`
- `cancel_order`

### Robinhood-Only Tools (≈10 tools)

**Crypto** (3 tools):
- `get_crypto_positions`
- `get_crypto_quote`
- `order_buy_crypto`

**Robinhood-Specific** (7 tools):
- `get_referrals`
- `get_subscription_fees`
- Some advanced portfolio features

### Schwab-Only Tools (≈5 tools, future)

**Streaming**:
- `stream_quotes` (real-time quote streaming)
- `stream_level2` (order book depth)

**Schwab-Specific**:
- TBD based on API exploration

---

## Appendix B: File Changes Summary

### New Files
- `src/open_stocks_mcp/brokers/__init__.py`
- `src/open_stocks_mcp/brokers/base.py`
- `src/open_stocks_mcp/brokers/registry.py`
- `src/open_stocks_mcp/brokers/robinhood.py`
- `src/open_stocks_mcp/brokers/schwab.py`
- `src/open_stocks_mcp/tools/broker_tools.py`
- `docs/SCHWAB_SETUP.md`
- `tests/unit/test_broker_registry.py`
- `tests/unit/test_schwab_broker.py`
- `tests/integration/test_schwab_*.py` (11 journey categories)

### Modified Files
- `src/open_stocks_mcp/config.py` - Add broker configurations
- `src/open_stocks_mcp/server/app.py` - Use broker registry
- `src/open_stocks_mcp/tools/error_handling.py` - Broker-agnostic errors
- `pyproject.toml` - Add schwab-py dependency
- `README.md` - Multi-broker examples
- `CLAUDE.md` - Schwab setup instructions
- `.env.example` - Schwab environment variables

### Deprecated Files (moved into brokers/)
- `src/open_stocks_mcp/tools/session_manager.py` → `brokers/robinhood.py`

---

**End of Plan**
