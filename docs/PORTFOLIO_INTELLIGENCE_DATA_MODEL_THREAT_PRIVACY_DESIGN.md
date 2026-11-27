# Portfolio Intelligence — data model and threat/privacy design

Status: design proposal only; no portfolio API, database schema, authentication behavior, or deployment control is represented as implemented by this document.

Related work: Issues #85 and #86.

## 1. Security and product invariants

1. A portfolio, holding, lot, transaction, alert, preference, and analysis request belongs to exactly one authenticated user (or an explicitly authorized shared-portfolio principal in a later reviewed extension).
2. Every read, write, export, background job, cache lookup, and analysis lookup is tenant-scoped on the server. A client-supplied owner/user ID is never an authorization decision.
3. Portfolio accounting is deterministic application logic. LLM output may explain computed facts but must never write balances, quantities, costs, fees, tax values, lot allocations, or realized P&L.
4. AI analysis receives only a minimized, read-only snapshot after authorization and data-eligibility checks. It cannot query another user's records or invoke trading/broker-order actions.
5. Missing, stale, unverified, or ineligible market inputs produce UNKNOWN/insufficient-evidence. Never substitute a guessed price or silently carry forward an old quote.
6. No auto-trading, order placement, guaranteed-return claim, or inferred user risk profile.

## 2. Proposed logical data model

| Entity | Required fields | Ownership and integrity |
|---|---|---|
| Portfolio | id, owner_user_id, name, base_currency, created_at, updated_at | owner immutable; unique scoped id |
| Holding | id, portfolio_id, symbol, horizon, risk_preference, status | portfolio must belong to caller; symbol validated against instrument registry |
| AcquisitionLot | id, holding_id, acquired_at, quantity, unit_price, fees, source | immutable acquisition facts; edits are corrections with audit history |
| Transaction | id, portfolio_id, holding_id, lot_id, type, trade_date, quantity, price, fees, taxes | append-only ledger; partial disposals allocate explicit lots |
| CorporateActionApplication | id, holding_id, event_id, applied_at, factor, evidence_ref | only verified/effective-dated events; never infer adjustment |
| ValuationSnapshot | id, portfolio_id, as_of, price, source_ref, eligibility, freshness | read-only point-in-time valuation; no unverified price promotion |
| Alert | id, owner_user_id, portfolio_id, rule, enabled, created_at | owner-scoped; explicit pause/disable; delivery audit |
| AnalysisSnapshot | id, owner_user_id, portfolio_id, as_of, input_manifest, result_ref | immutable input provenance; separates facts/calculations/assumptions/model narrative |
| AuditEvent | id, actor_user_id, owner_user_id, object_type, object_id, action, occurred_at | append-only; no sensitive values or secrets in logs |

All money values should use decimal arithmetic with explicit currency and scale rules; never binary floating-point for persisted accounting. Quantities and unit prices must be validated as finite and positive where applicable. Schema migrations must preserve existing records and support rollback/restore.

## 3. Authorization model

- Authenticate every portfolio route; deny by default.
- Resolve the principal from the verified server session/token, then scope every query by owner.
- Enforce ownership again on nested resources (holding, lot, transaction, alert, analysis); do not trust a parent ID supplied by the client.
- Use object-level authorization tests for read, create, update, delete, export, and background-job execution.
- Return a consistent not-found/forbidden policy that does not reveal whether another user's portfolio ID exists.
- Background workers must carry a server-issued owner scope and re-check it before reading or writing.
- Cache keys must include the authenticated tenant scope; shared caches must never key on portfolio ID alone.

## 4. Threat model and required controls

| Threat | Required control | Verification |
|---|---|---|
| IDOR / cross-user data leak | server-derived owner scope on every query and mutation | two-user API tests for every resource and nested route |
| Prompt injection in market/news/source text | treat external text as untrusted data; tool access allowlist; no portfolio mutation tools | adversarial content tests |
| LLM arithmetic drift | compute all financial outputs in deterministic decimal service; LLM read-only | golden fixtures and mutation-denial tests |
| Stale or fabricated market price | eligibility/freshness manifest; UNKNOWN state on failure | stale/missing/unverified price tests |
| Unauthorized export | owner-scoped authorization, re-authentication for bulk export, audit event | cross-user export denial |
| Secret/PII leakage in logs | structured redaction; no tokens, credentials, full holdings or raw personal notes in logs | log redaction tests |
| Replay/duplicate transactions | idempotency key plus immutable event identity | duplicate request/retry tests |
| Malicious or mistaken corporate action | evidence-gated event and explicit application record | unverified event cannot change quantity/cost |
| Alert abuse or unwanted disclosure | per-user controls, rate limits, verified destination, pause/disable | authorization and delivery-state tests |
| Backup/restore exposure | encrypted backups, least-privilege access, restore drill and retention policy | operational evidence; not assumed from code |

## 5. Deterministic accounting contract

- Cost basis is derived from acquisition lots and explicit disposal-allocation policy.
- Weighted-average cost, FIFO, or another method must be selected and documented per account/jurisdiction before implementation; do not silently mix methods.
- Realized and unrealized P&L, break-even, fees, and taxes are separately named outputs.
- Partial sells must allocate quantity and cost basis deterministically; quantities cannot become negative.
- Splits, bonus shares, rights, mergers, and symbol changes require verified event identity, effective date, ratio/terms, and auditable application.
- Every valuation states the price timestamp, source, freshness, eligibility, and whether fees/taxes are included.

Initial arithmetic fixture from Issue #85 (test-only, not market data): CFCL, 2,500 shares at NPR 593; hypothetical NPR 561 gives cost NPR 1,482,500, market value NPR 1,402,500, gross unrealized P&L -NPR 80,000 (-5.40%) before costs.

## 6. API and client boundaries

- Web and mobile use the same versioned API schemas and calculation fixtures.
- Client requests express intent; server computes and validates all financial state.
- Never accept a client-supplied market price as a verified valuation input.
- API responses include an as-of timestamp, freshness, evidence/eligibility state, and calculation version.
- UI must distinguish zero from missing, stale, unknown, and not-yet-loaded.
- Mobile/web local storage must not be treated as the authoritative portfolio ledger; sensitive cached content must be minimized and cleared on logout/account switch.

## 7. Release gates before production

1. Reviewed schema, threat model, retention policy, and jurisdiction-specific privacy requirements.
2. Authenticated CRUD with full object-level tenant-isolation tests.
3. Deterministic accounting golden fixtures including multiple lots, partial sells, fees/taxes, and verified corporate actions.
4. API contract parity for web/mobile; accessibility and empty/error/stale states.
5. Audit logging, rate limits, secret handling, backup/restore, encryption, and operational review.
6. Exact-head CI and independent security review.
7. Live market analysis remains disabled until its data sources independently pass existing session, lifecycle, source-rights, point-in-time, and quality gates.

## 8. Explicit non-claims

This document does not assert that authentication, encryption, tenant isolation, portfolio CRUD, accounting, mobile UI, backups, or production deployment already exist. It is a design baseline for review before implementation.
