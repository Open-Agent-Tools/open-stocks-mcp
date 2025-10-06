# Graceful Multi-Broker Authentication Implementation

**Status**: ✅ COMPLETE
**Branch**: `feature/schwab-integration`
**Commit**: d52e916

---

## Problem Solved

**Before**: If Robinhood login failed, the entire MCP server would crash with `sys.exit(1)`

**After**: Server starts successfully regardless of authentication status, allowing:
- Troubleshooting via `broker_status` tool
- Graceful error messages from tools
- Multiple brokers with partial authentication
- Server operation in limited mode

---

## Architecture

### New Broker Abstraction Layer

```
src/open_stocks_mcp/brokers/
├── __init__.py          # Public exports
├── base.py              # BaseBroker abstract class + BrokerAuthStatus enum
├── registry.py          # BrokerRegistry for managing multiple brokers
├── auth_coordinator.py  # Multi-broker authentication orchestration
└── robinhood.py         # RobinhoodBroker adapter (wraps SessionManager)
```

### Core Components

#### 1. BaseBroker (Abstract Interface)

```python
class BaseBroker(ABC):
    """Base class for all broker integrations"""

    @abstractmethod
    async def authenticate(self) -> bool:
        """Returns bool, never raises - updates self._auth_info on failure"""

    def is_available(self) -> bool:
        """Check if broker ready for trading"""

    def create_unavailable_response(self) -> dict:
        """Generate standardized error response"""
```

**Key Design**: Authentication methods return `bool`, never raise exceptions

#### 2. BrokerAuthStatus (Enum)

```python
class BrokerAuthStatus(Enum):
    NOT_CONFIGURED = "not_configured"      # No credentials
    NOT_AUTHENTICATED = "not_authenticated"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    AUTH_FAILED = "auth_failed"
    TOKEN_EXPIRED = "token_expired"
    MFA_REQUIRED = "mfa_required"
```

#### 3. BrokerRegistry (Centralized Management)

```python
class BrokerRegistry:
    """Manages all broker instances"""

    async def authenticate_all(self, fail_fast=False) -> dict[str, bool]:
        """Non-blocking: attempts all authentications, returns results"""

    def get_broker_or_error(self, name) -> tuple[Broker | None, dict | None]:
        """Returns (broker, None) if available, else (None, error_response)"""

    def get_auth_status(self) -> dict:
        """Full status for all brokers (for broker_status tool)"""
```

**Key Design**: Registry continues even if all brokers fail to authenticate

#### 4. AuthCoordinator (Orchestration)

```python
async def attempt_broker_logins(
    require_at_least_one: bool = False
) -> tuple[int, int, list[str]]:
    """
    Returns: (successful_count, total_count, failed_broker_names)

    Logs detailed summary:
    ✓ robinhood: Authenticated
    ✗ schwab: Invalid API key
    ⚠️ Partial success: 1/2 brokers authenticated
    """
```

#### 5. RobinhoodBroker (Adapter)

```python
class RobinhoodBroker(BaseBroker):
    """Wraps existing SessionManager for compatibility"""

    def __init__(self, username, password, session_manager):
        # Reuses existing SessionManager - no breaking changes

    async def authenticate(self) -> bool:
        success = await self.session_manager.ensure_authenticated()
        # Updates self._auth_info, returns bool
```

---

## Server Startup Flow

### Before (Blocking, Crash on Failure)

```
1. Prompt for credentials
2. Call attempt_login(username, password)
3. If login fails -> sys.exit(1) 💥 CRASH
4. Create MCP server
5. Start transport
```

### After (Non-Blocking, Graceful Degradation)

```
1. Prompt for credentials (can skip with Ctrl+C)
2. Create MCP server
3. Call setup_brokers(username, password)
   ├─ Register RobinhoodBroker (if credentials provided)
   ├─ Register SchwabBroker (TODO: when implemented)
   └─ attempt_broker_logins() - NON-BLOCKING
       ├─ Logs detailed authentication results
       └─ Returns success/failure counts
4. Start transport (ALWAYS proceeds) ✅
5. Tools check broker availability before execution
```

---

## New MCP Tools (2 Added)

### 1. `broker_status()` - Detailed Authentication Status

**Returns**:
```json
{
  "result": {
    "brokers": {
      "robinhood": {
        "status": "authenticated",
        "last_auth_attempt": "2025-10-06T12:30:45",
        "last_successful_auth": "2025-10-06T12:30:45",
        "error_message": null,
        "is_available": true,
        "is_configured": true,
        "requires_setup": false
      },
      "schwab": {
        "status": "not_configured",
        "is_available": false,
        "is_configured": false,
        "requires_setup": true,
        "setup_instructions": "Set SCHWAB_API_KEY and SCHWAB_APP_SECRET"
      }
    },
    "available_brokers": ["robinhood"],
    "total_configured": 1,
    "total_authenticated": 1
  }
}
```

### 2. `list_brokers()` - Quick Broker Overview

**Returns**:
```json
{
  "result": {
    "brokers": [
      {
        "name": "robinhood",
        "available": true,
        "status": "authenticated",
        "configured": true
      },
      {
        "name": "schwab",
        "available": false,
        "status": "not_configured",
        "configured": false
      }
    ],
    "count": 2
  }
}
```

---

## Tool Error Responses

When a tool is called but the broker is unavailable:

### Example: No Credentials

```json
{
  "result": {
    "error": "Robinhood is not configured. Please set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD environment variables.",
    "status": "broker_unavailable",
    "broker": "robinhood",
    "auth_status": "not_configured",
    "requires_setup": false
  }
}
```

### Example: Authentication Failed

```json
{
  "result": {
    "error": "Robinhood authentication failed: Invalid username or password",
    "status": "broker_unavailable",
    "broker": "robinhood",
    "auth_status": "auth_failed",
    "requires_setup": false
  }
}
```

### Example: Session Expired

```json
{
  "result": {
    "error": "Robinhood session expired. Please restart the server to re-authenticate.",
    "status": "broker_unavailable",
    "broker": "robinhood",
    "auth_status": "token_expired",
    "requires_setup": false
  }
}
```

---

## Testing Scenarios

### Scenario 1: No Credentials (Server Starts Successfully)

```bash
# No environment variables set
$ uv run open-stocks-mcp-server --transport http --port 3001

# Output:
⚠️  Robinhood credentials not provided - skipping Robinhood integration
   Set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD to enable Robinhood
Authentication Summary (0.1s)
  ○ ROBINHOOD: Not configured (skipped)
⚠️  No brokers authenticated (1 attempted)
Server ready - broker tools available based on authentication status
```

**Result**: Server starts ✅, tools return `not_configured` errors

### Scenario 2: Wrong Password (Server Starts Successfully)

```bash
export ROBINHOOD_USERNAME=user@example.com
export ROBINHOOD_PASSWORD=wrongpassword
$ uv run open-stocks-mcp-server --transport http --port 3001

# Output:
Configuring Robinhood broker...
✓ Robinhood broker registered
Authenticating with Robinhood...
✗ Robinhood authentication failed
Authentication Summary (2.5s)
  ✗ ROBINHOOD: Invalid username or password
❌ No brokers authenticated (1 attempted)
   Server will start but all broker-specific tools will be unavailable
Server ready - broker tools available based on authentication status
```

**Result**: Server starts ✅, tools return `auth_failed` errors

### Scenario 3: Valid Credentials (Server Starts Successfully)

```bash
export ROBINHOOD_USERNAME=user@example.com
export ROBINHOOD_PASSWORD=correctpassword
$ uv run open-stocks-mcp-server --transport http --port 3001

# Output:
Configuring Robinhood broker...
✓ Robinhood broker registered
Authenticating with Robinhood...
✓ Robinhood authentication successful
Authentication Summary (1.8s)
  ✓ ROBINHOOD: Authenticated
✅ All 1 broker(s) authenticated successfully
Server ready - broker tools available based on authentication status
```

**Result**: Server starts ✅, all tools work normally

### Scenario 4: Interactive Prompt (Can Skip)

```bash
# No env vars, interactive terminal
$ uv run open-stocks-mcp-server --transport http --port 3001

# Output:
No credentials provided - prompting for Robinhood credentials
(Press Ctrl+C to skip and start without Robinhood)
Robinhood username (or press Ctrl+C to skip): ^C

Skipping Robinhood authentication
⚠️  Robinhood credentials not provided - skipping Robinhood integration
Server ready - broker tools available based on authentication status
```

**Result**: User can skip authentication, server starts anyway ✅

---

## Backwards Compatibility

### ✅ Preserved (No Breaking Changes)

- All existing tool names unchanged
- SessionManager logic reused (no modifications)
- Environment variables work identically
- Pickle file locations unchanged
- All existing tests pass (after version number fixes)

### 🔄 Changed (Improved Behavior)

- **Before**: `sys.exit(1)` on auth failure → **After**: Server starts anyway
- **Before**: Single global session → **After**: Per-broker sessions (via registry)
- **Before**: No auth status visibility → **After**: `broker_status()` and `list_brokers()` tools

### ⚠️ Deprecated (But Still Works)

- `attempt_login()` function - replaced by `setup_brokers()`
- Direct SessionManager usage in tools - will migrate to broker adapters

---

## Migration Guide

### For Existing Users (No Action Required)

Current setup continues to work:
```bash
export ROBINHOOD_USERNAME=user@example.com
export ROBINHOOD_PASSWORD=password
uv run open-stocks-mcp-server --transport http --port 3001
```

**Behavior Change**: If credentials are wrong, server starts instead of crashing

### For Docker Deployments

Previously crashed on bad credentials:
```yaml
environment:
  - ROBINHOOD_USERNAME=wrong
  - ROBINHOOD_PASSWORD=wrong
# Container would crash immediately
```

Now starts in limited mode:
```yaml
environment:
  - ROBINHOOD_USERNAME=wrong
  - ROBINHOOD_PASSWORD=wrong
# Container starts, health check passes
# Tools return auth_failed errors
# Can troubleshoot via broker_status tool
```

### For Adding Schwab (Future)

```bash
# Enable both brokers
export ROBINHOOD_USERNAME=user@example.com
export ROBINHOOD_PASSWORD=password
export SCHWAB_API_KEY=your_api_key
export SCHWAB_APP_SECRET=your_secret

# Server registers both, attempts authentication
# Succeeds with either, both, or neither
# Use broker_status to check which are available
```

---

## Next Steps

### Completed ✅
- [x] Broker abstraction layer (BaseBroker)
- [x] Broker registry (BrokerRegistry)
- [x] Auth coordinator (attempt_broker_logins)
- [x] Robinhood adapter (RobinhoodBroker)
- [x] Graceful startup (setup_brokers)
- [x] Status tools (broker_status, list_brokers)
- [x] Error responses (create_unavailable_response)
- [x] Server no longer crashes on auth failure

### Pending ⏳
- [ ] Unit tests for broker registry
- [ ] Integration tests for partial auth scenarios
- [ ] Update existing tools to use broker adapter
- [ ] Schwab broker implementation (Phase 3)
- [ ] Multi-broker tool registration (Phase 4)

---

## Code Changes Summary

**Files Added (5)**:
- `src/open_stocks_mcp/brokers/__init__.py` (14 lines)
- `src/open_stocks_mcp/brokers/base.py` (244 lines)
- `src/open_stocks_mcp/brokers/registry.py` (327 lines)
- `src/open_stocks_mcp/brokers/auth_coordinator.py` (118 lines)
- `src/open_stocks_mcp/brokers/robinhood.py` (204 lines)

**Files Modified (2)**:
- `src/open_stocks_mcp/server/app.py`:
  - Removed `sys.exit(1)` calls (2 locations)
  - Added `setup_brokers()` async function
  - Added `broker_status()` MCP tool
  - Added `list_brokers()` MCP tool
  - Updated `main()` for graceful auth
  - Added graceful logout on shutdown

- `src/open_stocks_mcp/server/http_transport.py`:
  - Added root endpoint (`/`)
  - Added SSE endpoint (`/sse`)

**Total Lines**: +907 lines of broker abstraction, -2 lines of `sys.exit(1)`

---

## Benefits

### For Users
- ✅ Server runs even with authentication issues
- ✅ Clear error messages explain what's wrong
- ✅ Can troubleshoot via `broker_status` tool
- ✅ Can skip authentication in interactive mode
- ✅ Multiple brokers supported (Robinhood now, Schwab soon)

### For Developers
- ✅ Clean abstraction for adding new brokers
- ✅ Testable authentication flows (no sys.exit)
- ✅ Centralized broker management
- ✅ Consistent error handling
- ✅ Easy to add Schwab, Fidelity, etc.

### For Operations
- ✅ Docker containers don't crash on bad credentials
- ✅ Health checks pass even without auth
- ✅ Can monitor auth status via MCP tools
- ✅ Graceful degradation vs total failure
- ✅ Better logging and observability

---

## Example: Full Authentication Flow

```python
# 1. Server Startup
server = create_mcp_server()
await setup_brokers(username, password)

# 2. Broker Registration (in setup_brokers)
registry = await get_broker_registry()
robinhood_broker = RobinhoodBroker(username, password, session_manager)
registry.register(robinhood_broker)

# 3. Authentication Attempt (in setup_brokers)
results = await registry.authenticate_all(fail_fast=False)
# Returns: {"robinhood": True} if successful

# 4. Server Starts (ALWAYS)
await server.run_stdio_async()  # or run_http_server()

# 5. Tool Execution
@mcp.tool()
async def portfolio():
    broker, error = await get_authenticated_broker_or_error()
    if error:
        return error  # Descriptive error response
    return await broker.get_portfolio()

# 6. Status Check (New Tool)
@mcp.tool()
async def broker_status():
    registry = await get_broker_registry()
    return registry.get_auth_status()
```

---

## Conclusion

The graceful authentication system transforms the MCP server from:
- **Fragile** (crashes on auth failure) → **Resilient** (runs in limited mode)
- **Single broker** (Robinhood only) → **Multi-broker** (extensible architecture)
- **Opaque** (why did it crash?) → **Observable** (broker_status tool)
- **Binary** (works or crashes) → **Gradual** (partial authentication supported)

This foundation enables the Schwab integration (Phase 3) and future broker additions without breaking existing functionality.

**Status**: Ready for testing and Schwab implementation 🚀
