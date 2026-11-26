# P1.8–P1.12 acceptance checkpoint — 2026-11-27

This is a review of existing repository evidence, not a new full-archive validation run. No canonical promotion or raw data changes authorized.

| Gate | Status | Evidence |
|---|---|---|
| P1.8 price/volume/turnover | PARTIAL | 281 equity files, 146132 provider-supported equity-date bars, 132346 reconciled transaction totals, 11628 bars without contract observations; scanner issue #6 |
| P1.9 floorsheet completeness | PARTIAL | 928 blobs inventoried, integrity workflow passed; content-level audit pending; SMC issue #74 and draft PR #80 |
| P1.10 corporate actions | OPEN | Effective-dated lifecycle and adjustment basis remain incomplete; scanner issue #20 |
| P1.11 provenance | PARTIAL | 1368 OHLCV flags UNKNOWN; 1283 matching invalid tuples and 85 absent; independent source not established; SMC issue #56 |
| P1.12 acceptance | BLOCKED | No production backtest or AI recommendation approval |

## Next executable priority
Continue SMC issue #74 / draft PR #80 content-level audit on its pinned base, separating exact duplicate rows, conflicting business keys, repeated valid candles and date anomalies. Preserve raw archives. Record omissions, row-level evidence, source hashes, and deterministic regression tests. Do not count inventory-only files as parsed. Keep P4.40 postponed.

## Evidence
- https://github.com/jaljala044/nepse-elite-ai-scanner-pro/issues/6
- https://github.com/jaljala044/nepse-elite-ai-scanner-pro/issues/20
- https://github.com/jaljala044/nepse-smc-data/issues/56
- https://github.com/jaljala044/nepse-smc-data/issues/74
- https://github.com/jaljala044/nepse-smc-data/actions/runs/45889555286

No new historical corrections, CI runs, or primary-source validations were performed for this checkpoint.