# Portfolio API Contract v1 — Slice A

**Status:** proposed contract; not deployed or authenticated.  
**Parent:** Issue #85 / Issue #86.  
**Safety:** portfolio endpoints must remain unavailable until server-side authentication and per-resource authorization are implemented and independently tested.

## Contract invariants

1. The authenticated principal is the sole source of portfolio ownership. There is no `owner_id` in request bodies, query parameters, or client-controlled headers.
2. Every operation scopes by both authenticated principal and resource ID. A foreign owner's resource is indistinguishable from a missing resource (404).
3. Holdings and transactions are private user data. Never return another principal's rows, even when a valid UUID is supplied.
4. Transactions are immutable ledger entries in this MVP. Corrections require a separately audited reversal/amendment workflow; no silent update.
5. Quantities are positive whole shares. Prices and fees are decimal strings on the wire to avoid binary floating-point ambiguity.
6. Accounting uses the deterministic weighted-average-cost domain function. No market mark is inferred from scanner/CSV uploads.
7. Missing, stale, unverified or ineligible market evidence yields `UNKNOWN`; no live valuation or recommendation is authorized by this API contract.
8. No broker orders, automated execution, guaranteed-return language or automatic corporate-action adjustment.

## Authentication and common errors

All routes require a server-authenticated session or bearer token. Authentication middleware must derive a stable principal ID, pass it to the persistence layer, and reject anonymous requests before calling it.

- `401`: no valid authenticated principal.
- `404`: resource absent or not owned by the authenticated principal.
- `409`: duplicate transaction ID or conflicting immutable operation.
- `422`: invalid symbol, horizon, risk preference, date, quantity, price, fee or accounting sequence.
- `503`: portfolio persistence unavailable; do not fall back to the OHLCV database or in-memory state.

Do not disclose whether a foreign resource ID exists.

## Proposed routes

| Method | Route | Request | Response |
|---|---|---|---|
| POST | `/v1/portfolios` | `{name}` | portfolio object |
| GET | `/v1/portfolios` | none | `{items: []}` |
| PATCH | `/v1/portfolios/{portfolio_id}` | `{name}` | portfolio object |
| DELETE | `/v1/portfolios/{portfolio_id}` | none | `204` |
| POST | `/v1/portfolios/{portfolio_id}/holdings` | symbol, horizon, risk_preference | holding object |
| GET | `/v1/portfolios/{portfolio_id}/holdings` | none | `{items: []}` |
| POST | `/v1/portfolios/{portfolio_id}/holdings/{holding_id}/transactions` | transaction fields | transaction object |
| GET | `/v1/portfolios/{portfolio_id}/holdings/{holding_id}/transactions` | none | `{items: []}` |

## Wire schemas

### Portfolio
```json
{
  "portfolio_id": "server-generated UUID",
  "name": "Long-term",
  "created_at": "RFC3339 timestamp",
  "updated_at": "RFC3339 timestamp"
}
```

### Holding
```json
{
  "holding_id": "server-generated UUID",
  "symbol": "CFCL",
  "horizon": "long_term",
  "risk_preference": "balanced",
  "created_at": "RFC3339 timestamp"
}
```

Allowed horizons: `short_term`, `one_to_three_months`, `three_to_six_months`, `long_term`.  
Allowed risk preferences: `capital_protection`, `balanced`, `aggressive_growth`.

### Transaction create request
```json
{
  "transaction_id": "optional client idempotency key",
  "transaction_type": "buy",
  "trade_date": "2026-11-27",
  "quantity": 10,
  "unit_price": "100.00",
  "fees": "10.00"
}
```

The server validates the full chronological ledger and oversell constraints before insert. A duplicate transaction ID is rejected. No client-provided owner, average cost, market price, P&L, source eligibility or recommendation fields are accepted.

### Position accounting response
```json
{
  "share_quantity": "10",
  "remaining_cost_basis": "1010.00",
  "average_cost_per_share": "101.00",
  "realized_pnl": "0",
  "market_value": null,
  "unrealized_pnl": null,
  "market_mark_status": "UNKNOWN",
  "as_of": null
}
```

Numeric accounting values are serialized as decimal strings. Market value and unrealized P&L remain null unless a separately authorized market-data adapter supplies a verified, eligible, point-in-time mark. Slice A does not implement that adapter.

## Required acceptance tests before routes are enabled

- Anonymous access is rejected for every route.
- Principal A cannot list, read, rename, delete or append transactions to Principal B resources.
- Resource UUID guessing returns the same 404 response as an absent resource.
- Client-supplied `owner_id` is rejected/ignored and never controls authorization.
- Cross-portfolio and cross-holding transaction IDs cannot be used to bypass ownership.
- Duplicate idempotency keys, backdated transactions, fractional quantities and oversells fail without writes.
- Persistence failure returns 503 and never falls back to public market-data storage.
- OpenAPI documents auth requirements and contains no owner field in public request schemas.
- Browser/mobile clients consume the same schemas and shared calculation fixtures.

## Explicitly deferred

Authentication implementation, rate limits, audit-event retention, encryption/key management, database migrations/backup/restore, API route implementation, UI clients, taxes, corporate actions, market valuation, sector exposure, alerts and AI-generated holding analysis. These remain acceptance work, not implied capabilities.
