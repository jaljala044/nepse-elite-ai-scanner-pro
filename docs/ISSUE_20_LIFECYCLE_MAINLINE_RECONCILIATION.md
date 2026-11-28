# Issue #20 — lifecycle eligibility and session finality

- Preserve the mainline retained-payload SHA-256 validation and Issue #5 archive quarantine.
- Require an explicit session-evidence mapping; no silent provenance default.
- Interpret cutoffs in Asia/Kathmandu and reject expected sessions beyond the local cutoff date.
- Require same-day session finality evidence, bound to exact date, status and complete finality, available and finalized before cutoff.
- Tests cover future dates, missing/valid/late finality and archive-quarantine compatibility.
- Evaluator remains exploratory only; no production signal or canonical promotion is enabled. Synthetic tests are not exchange evidence.
