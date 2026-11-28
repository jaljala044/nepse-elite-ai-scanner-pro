# Portfolio Slice A — persistence foundation

This slice adds owner-scoped DuckDB persistence primitives for portfolios, holdings and acquisition/disposal transactions.

## Security boundary
- Every repository operation requires an `owner_id` supplied by a trusted authentication layer.
- The owner identifier is never accepted from a user-controlled request body by this module.
- Every portfolio/holding/transaction query is scoped by owner and parent identifiers.
- The module is intentionally **not wired to HTTP routes**: the current API has no verified authenticated-principal dependency. Exposing these functions through unauthenticated routes would create an IDOR/data-disclosure vulnerability.
- Do not treat a caller-provided owner string as authenticated identity.

## Accounting boundary
- Transaction inputs use whole-share quantities and finite Decimal-compatible prices/fees.
- Transactions are appended chronologically; duplicate transaction IDs are rejected by the database primary key.
- The existing pure `calculate_position` calculator remains the sole accounting authority; persistence does not calculate P&L or invent marks.
- Corporate actions, taxes, market valuation, alerts and auto-trading are not implemented here.

## Durability boundary
- The store uses a separate `NEPSE_PORTFOLIO_DATABASE` DuckDB file by default.
- This is a local persistence implementation, not proof of multi-process production durability, encryption, backup, restore or deployment readiness.
- Production API exposure requires authenticated subject integration, authorization tests, migration/backup design and independent security review.
