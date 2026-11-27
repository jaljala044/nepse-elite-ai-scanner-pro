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


## 9. Implementation sequence and acceptance evidence

The design should be implemented in independently reviewable increments; do not treat this document as evidence that any phase already exists.

1. **Persistence and migrations:** add portfolio, holding, lot, transaction, corporate-action application, valuation, alert, analysis snapshot, and audit-event storage. Include tenant ownership, foreign-key constraints, decimal types, immutable ledger semantics, migration rollback, and restore tests.
2. **Authorization boundary:** derive the principal only from the authenticated server context. Add tenant-scoped repository/service methods and two-user isolation tests for every nested resource, export, and background job before exposing CRUD.
3. **Accounting engine:** implement the selected cost-basis method and explicit fee/tax configuration with decimal arithmetic. Add golden fixtures for multiple lots, partial sells, fees, negative-quantity rejection, realized/unrealized P&L, and break-even.
4. **Evidence-bound valuation:** consume only existing eligible market snapshots. Return UNKNOWN for missing, stale, unverified, or out-of-scope prices; attach source, timestamp, freshness, and eligibility to every result. Corporate actions must be independently verified before application.
5. **Shared API contract:** publish versioned request/response schemas and deterministic fixtures used by both web and mobile clients. Keep client-supplied user IDs and prices out of authorization/accounting decisions.
6. **Client experiences:** implement beginner and professional views over the same API, including explicit loading, empty, stale, unknown, error, and audit/provenance states. Keep local storage non-authoritative and clear sensitive cache on account switch/logout.
7. **Security/release review:** run object-level authorization, prompt-injection, redaction, idempotency, rate-limit, backup/restore, accessibility, and independent security tests. Keep production rollout disabled until all release gates in Section 7 pass.

Each phase must ship with its own migration/test evidence and exact-head CI result. Do not merge a later phase by copying or reimplementing a completed phase; extend the accepted contract and record its owner/status first.

The current PR remains a design-only proposal. No API, database migration, tenant-isolation control, accounting engine, web/mobile screen, encryption, or deployment is claimed as implemented by this sequence.

## 10. Retention, deletion, export, and jurisdiction decisions

These are product and legal-policy prerequisites, not implementation claims:

- Publish a data inventory and retention schedule for portfolio records, transaction corrections, analysis snapshots, alerts, audit events, support artifacts, application logs, and backups. Assign an owner and purpose to each category.
- Provide an authenticated account export that includes the user's portfolio data, transaction history, calculation/configuration metadata, and machine-readable timestamps. Re-authorize the export request, scope it to the authenticated tenant, audit the export event, and prevent public or guessable download links.
- Define account deletion as a documented workflow. Identify which personal/profile data can be erased, which financial/audit records must be retained under applicable law, the lawful basis and retention period for each exception, and how retained records are minimized or pseudonymized. Do not silently promise full erasure where a legal retention duty applies.
- Specify backup expiry and deletion propagation: deleted or expired records must age out of immutable backups on a stated schedule, with restore procedures that reapply deletion tombstones before restored data becomes available. Record the maximum backup-retention window and test the process.
- Minimize audit logs: retain actor, tenant, object reference, action, timestamp, and outcome where justified; exclude secrets, full holdings, raw notes, and unnecessary personal data. Define access controls and retention for audit events separately from transaction records.
- Before enabling tax-aware calculations, obtain a product/legal decision for supported jurisdictions, base currency, tax treatment, and the selected cost-basis method. The current Slice A weighted-average implementation is an accounting prototype, not a declaration that weighted average is legally appropriate in every jurisdiction. Store the applicable method/configuration with effective dates and preserve an auditable history when it changes.
- Do not launch jurisdiction-specific tax, deletion, export, or retention claims until reviewed by qualified privacy/legal owners for the actual operating markets.
