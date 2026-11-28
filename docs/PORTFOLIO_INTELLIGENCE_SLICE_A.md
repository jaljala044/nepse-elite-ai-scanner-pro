# Portfolio Intelligence — Slice A foundation

Issue: #85  
Branch: `feature/issue-85-portfolio-foundation`

## Delivered in this slice

- Private per-user portfolio create/list/read/rename endpoints; user-visible deletion is an owner-scoped tombstone, not a physical row delete.
- Authenticated routes reuse the existing trusted reverse-proxy principal contract. The API does not accept a user-supplied owner identifier.
- Append-only buy/sell transaction ledger with an optional owner-scoped idempotency key.
- Deterministic weighted-average cost accounting. Buy fees are capitalized into cost basis; sell fees reduce net proceeds; partial disposals realize P&L and proportionally reduce remaining basis.
- Oversells and backdated transactions that would make chronological holdings negative are rejected.
- SQLite persistence is isolated in `NEPSE_PORTFOLIO_DB`; user ownership is enforced in every query and delete. Existing databases receive an additive `deleted_at` column migration.
- Tests cover the CFCL acceptance arithmetic, weighted-average cost, realized P&L, partial sales, oversell, concurrent replay/idempotency, owner isolation across nested routes, invalid/non-finite values, failed-write rollback, authentication and API CRUD.

## API

- `GET /v1/portfolios`
- `POST /v1/portfolios`
- `GET /v1/portfolios/{portfolio_id}`
- `PATCH /v1/portfolios/{portfolio_id}`
- `DELETE /v1/portfolios/{portfolio_id}`
- `GET /v1/portfolios/{portfolio_id}/transactions`
- `POST /v1/portfolios/{portfolio_id}/transactions`
- `GET /v1/portfolios/{portfolio_id}/positions`

Every route requires the configured trusted-proxy identity headers and secret. The proxy must strip client-supplied identity headers before injecting verified values, as required by the existing `private_accounts.principal` contract.

## Accounting rules

- Buy total cost = quantity × execution price + buy fees.
- Weighted average cost = remaining cost basis ÷ remaining quantity.
- Sell realized P&L = quantity × execution price − sell fees − quantity × weighted average cost immediately before the sale.
- A sale cannot exceed the shares held at that point in chronological transaction order. For transactions sharing the same trade date and timestamp, the append-only SQLite row insertion sequence is the deterministic tie-breaker; random transaction IDs are not used to reorder same-day events.
- Deleting a portfolio sets `deleted_at`; portfolio, position and transaction API reads then return not-found, while the immutable transaction rows remain retained and inaccessible through normal owner APIs.
- Monetary arithmetic uses Python `Decimal`; the ledger stores decimal strings.
- Idempotent replay with the same key and identical payload returns the original transaction. Reusing a key for a different payload fails.

## Explicitly not enabled

- No market price is fetched or trusted by this slice. Market value and unrealized P&L remain `null` / UNKNOWN until a timestamped eligible price source is integrated.
- No unverified corporate-action adjustment changes share quantity or cost basis.
- No AI commentary, recommendation, BUY/SELL signal, order placement or auto-trading is exposed.
- This does not establish production deployment, proxy configuration, encryption, backups or operational readiness.
- Account-level erasure and the applicable transaction-retention schedule are not implemented or decided here; they require a separate privacy/legal policy and an explicit, audited erasure mechanism.

## Acceptance fixture

CFCL 2,500 shares at NPR 593 produces cost basis NPR 1,482,500. At a hypothetical NPR 561 reference price, gross unrealized P&L would be -NPR 80,000 (-5.40%) before fees. The fixture is arithmetic-only and is not live market data or investment advice.
