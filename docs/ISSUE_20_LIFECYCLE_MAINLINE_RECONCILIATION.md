# Issue #20 — lifecycle eligibility reconciled with current main

## Ten implementation items

1. Rebase the lifecycle eligibility hardening on the latest mainline after Issue #4 exception-scope reconciliation.
2. Preserve the current primary-evidence contract, including base64-retained payload bytes and recomputed SHA-256.
3. Preserve the Issue #5 `Quarantine` archive-overlay guard and its mandatory behavior for archive-located records.
4. Require an explicit `session_evidence` mapping; callers cannot silently omit session provenance.
5. Interpret the decision cutoff in Nepal market time (Asia/Kathmandu).
6. Reject expected exchange sessions later than the Nepal-local decision date.
7. Require same-day session finality evidence for a session on the cutoff date.
8. Bind finality claims to the exact date, session classification and complete-finality status.
9. Require finalization to be available by the decision cutoff and to resolve to the same Nepal-local session date.
10. Add regression coverage for future dates, absent/valid/late finality and preservation of archive quarantine.

## Critical compatibility correction

The older PR #343 branch removed the archive overlay import and guard while it was behind main. That would have regressed the current Issue #5 archive quarantine controls. This mainline implementation retains those controls and the raw-payload SHA-256 validation from main.

## Safety

The evaluator remains descriptive/research-only. It does not repair, fill, adjust or join across instrument identity boundaries. Passing this evaluator only establishes exploratory replay eligibility under supplied evidence; approved backtests and production promotion remain disabled. All fixtures are synthetic and do not establish official NEPSE session evidence.
