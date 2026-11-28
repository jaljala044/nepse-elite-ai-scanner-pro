# Private Portfolio API — Slice A

**Status:** implementation in review; not a production deployment certification.  
**Authentication:** every route requires the trusted reverse-proxy identity contract. The proxy must strip client-supplied identity headers and inject `x-nepse-subject` only after authentication, with `x-nepse-proxy-secret` matching the server-side secret. The backend rejects missing/invalid credentials. Do not expose the secret to browser or mobile clients.

## Routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/v1/portfolios` | List authenticated user's portfolios |
| POST | `/v1/portfolios` | Create portfolio |
| GET | `/v1/portfolios/{portfolio_id}` | Read one owned portfolio |
| PATCH | `/v1/portfolios/{portfolio_id}` | Rename an owned portfolio |
| DELETE | `/v1/portfolios/{portfolio_id}` | Soft-delete/hide portfolio; ledger retention is separate |
| GET | `/v1/portfolios/{portfolio_id}/positions` | Deterministic position accounting |
| GET/POST | `/v1/portfolios/{portfolio_id}/transactions` | Read or append immutable buy/sell ledger rows |
| GET | `/v1/portfolios/{portfolio_id}/preferences` | List holding preferences |
| PUT | `/v1/portfolios/{portfolio_id}/preferences/{symbol}` | Upsert a holding's horizon and risk preference |

## Holding preference request

```json
{
  "horizon": "one_to_three_months",
  "risk_preference": "capital_protection"
}
```

Allowed horizons: `short_term`, `one_to_three_months`, `three_to_six_months`, `long_term`.

Allowed risk preferences: `capital_protection`, `balanced`, `aggressive_growth`.

The preference key is the authenticated owner + portfolio + normalized symbol. Repeating PUT updates the existing preference rather than creating duplicates. Foreign-owner or missing portfolios return 404. Invalid values return 422.

## Accounting and data rules

- Share quantities must be positive whole shares; prices and fees use Decimal values.
- Buy fees are capitalized into weighted-average cost; sale fees reduce proceeds.
- Duplicate idempotency keys with identical transaction payloads return the original transaction; conflicting reuse is rejected.
- Oversells and backdated ledger sequences that create negative historical positions are rejected.
- Market value and unrealized P&L remain UNKNOWN until a separately eligible, timestamped market mark is connected.
- Corporate actions are not auto-applied unless verified event handling is added.
- Preferences are user intent only; they do not create a BUY/SELL recommendation or override data-quality gates.
- No order placement, auto-trading or guaranteed-return claims.

## Web/mobile contract

Web and mobile clients must use the same routes, enums, error semantics and Decimal-safe string serialization. Client requests must never include an owner identifier. The server derives ownership exclusively from the authenticated principal. Keep UI state private and avoid caching portfolio responses in shared/public caches.


## Private response caching

Every `/v1/portfolios` response, including authentication failures and mutation responses, is returned with `Cache-Control: private, no-store, max-age=0` and `Pragma: no-cache`. Reverse proxies and CDNs must preserve these headers and must not override them with shared-cache rules. Clients must not persist portfolio payloads in shared caches or analytics logs.
