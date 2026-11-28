# Issue #20 — lifecycle eligibility reconciled with current main

## Implementation

- Preserve raw-payload base64 validation and recomputed SHA-256.
- Preserve the Issue #5 archive quarantine import and mandatory guard for archive rows.
- Require explicit session evidence; callers cannot omit session provenance.
- Interpret decision cutoff in Asia/Kathmandu and reject expected sessions later than the local decision date.
- Require same-day session finality evidence bound to date, status, complete finality, and a finalization timestamp no later than the cutoff.
- Add synthetic regression tests for future sessions, absent/valid/late finality, and archive guard retention.

## Safety

The evaluator remains descriptive and research-only. Passing it establishes exploratory replay eligibility only under supplied evidence. It does not repair OHLCV, establish real NEPSE sessions, approve backtests, or authorize production promotion.
