# Broker Capability Remediation Path

Issue #244 locks the remediation path for the partially merged broker capability
baseline originally tracked by #237.

## Decision

Path A is selected: keep the broker capability and Schwab streaming baseline,
then complete the missing runtime contract. Path B, deleting the capability test
and Schwab stream manager, is rejected unless a human maintainer explicitly
supersedes issue #244.

The decision is intentionally scoped as a contract. The implementation belongs
to #245 or an equivalent pull request that closes the same runtime gap. Final
validation and linked-issue reconciliation belong to #246.

## Implementation Checklist

The implementation slice must satisfy this code contract:

- Add `BrokerCapabilities` in `src/open_stocks_mcp/brokers/base.py` with
  default `False` booleans for `streaming_quotes`, `options`, and `crypto`.
- Initialize `self._capabilities = BrokerCapabilities()` in
  `BaseBroker.__init__`.
- Add `BaseBroker.get_health_status()` returning `broker`, `is_available`,
  `auth_status`, `capabilities`, and `streaming_ready`.
- Keep `src/open_stocks_mcp/brokers/schwab_stream.py` and wire
  `SchwabBroker` to expose a single owned `SchwabStreamManager` consumer.
- Preserve `tests/unit/test_capabilities_and_streaming.py` as the canonical
  regression contract for the broker capability and stream-manager surface.

## Required Validation

The chosen path is not complete until both collection commands are clean:

```bash
uv run pytest tests/unit/test_capabilities_and_streaming.py --collect-only
uv run pytest tests/unit/ --collect-only
```

The implementation slice should also run the targeted behavior suite:

```bash
uv run pytest tests/unit/test_capabilities_and_streaming.py -v
```

## Issue #200 Handling

Issue #200 only applies if the shipped capability surface includes a
`BrokerCapability` enum or a broker capability map. In that case,
`EXTENDED_HOURS` must be represented for both Robinhood and Schwab, even if the
value is explicitly unsupported.

If the shipped surface remains the simple `BrokerCapabilities` dataclass, #200
should be re-scoped to an `extended_hours: bool = False` dataclass field or
closed as obsolete with a comment explaining that no enum capability map exists.
