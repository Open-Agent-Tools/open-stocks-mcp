# Agent Identity and Per-Tool Authorization

SECURITY.md covers session token encryption, API key authentication, and
HTTP transport security. This guide covers a different question: when
multiple agents or third-party tools connect to your Open Stocks MCP server,
how do you verify which agent is acting and restrict what tools it can call?

## When this matters

- Multiple agents share the same broker credentials (Robinhood, Schwab, or both)
- A third-party tool or wrapper connects to your MCP server
- You want to attribute trades to specific agent software for debugging or operational visibility
- You want to restrict some agents to market data only (no order placement)

## Pattern: authorization proxy

Place a reverse proxy between agents and the Open Stocks MCP server. The
proxy verifies agent credentials and enforces a per-tool permission policy
before forwarding requests. The MCP server does not need code changes.

```
Agent → Authorization Proxy (verify + enforce) → open-stocks-mcp
```

The proxy should:
1. Verify the agent's identity (signed attestation, API key, certificate, etc.)
2. Check the requested tool against a permission policy
3. Reject unauthorized or replayed requests
4. Log the decision for troubleshooting and accountability

This complements the existing `MCP_API_KEY` bearer-token auth, which
verifies that a request is authorized to reach the server. The proxy adds
a layer that distinguishes *which* authorized agent is calling *which* tool.

## Example tool permission tiers

Open Stocks MCP exposes tools across multiple brokers with different risk
levels. As an illustrative starting point, you might group them like this:

| Tier | Example tools | Rationale |
|------|--------------|-----------|
| Read-only | `get_portfolio`, `get_stock_quote`, `get_movers`, `schwab_get_portfolio`, `schwab_get_quotes` | No side effects |
| Write | `cancel_stock_order`, `schwab_cancel_order` | Modifies state but does not create new exposure |
| Trade | `place_stock_order`, `schwab_buy_stock_market`, `schwab_sell_stock_market` | Creates financial exposure |
| Trade (high-risk) | `schwab_buy_option`, `schwab_sell_option`, `schwab_buy_spread` | Options and complex orders |

> **This is illustrative, not exhaustive.** Check the
> [tool reference](api/tools.md) for the current tool list and review each
> tool's risk level before building your policy. Tools may be added or
> renamed between versions.

An agent authorized for "Read-only" should not be able to call
`place_stock_order`. The proxy enforces this before the request reaches
the MCP server.

## Implementation options

Several approaches can implement this pattern:

- **API gateway with tool-name routing** (e.g., nginx + Lua, Envoy, Kong):
  inspect the JSON-RPC `params.name` field and enforce allow/deny rules
  per agent identity.
- **MCP-aware auth proxy** (e.g., [@bolyra/gateway](https://github.com/bolyra/bolyra/tree/main/integrations/gateway)):
  a reverse proxy purpose-built for MCP servers with per-tool policy
  enforcement and decision logging.
- **Custom middleware**: wrap the MCP server's HTTP transport with
  authentication and authorization checks.

The choice depends on your deployment topology and trust model.

## What the proxy should log

For each `tools/call` request, the proxy should record:
- Agent identity (however you identify agents)
- Tool name requested
- Decision (allowed or denied)
- Timestamp
- Reason for denial (if applicable)

This creates a record that answers "which software placed this trade?"
or "which agent submitted that options order?"

## Relationship to existing security

| Layer | Protects | Documented in |
|-------|----------|---------------|
| Token encryption | Broker session tokens at rest | [SECURITY.md](../SECURITY.md) |
| API key auth | Network access to HTTP transport | [SECURITY.md](../SECURITY.md) |
| Agent authorization | Which agent can call which tools | This guide |

All three layers are independent. Token encryption protects credentials
at rest. API key auth gates network access. Agent authorization restricts
what each authenticated agent can do.
