# Issue #5 — cross-source equity session-gap overlap

**Date:** 2026-11-28  
**Source workflow:** PR #405, run 46175577631  
**Source artifact:** issue5-full-source-gap-inventory, artifact 15275272939  
**Artifact SHA-256:** ffec8dc4fd5cf1fb6b9e1c45350d71bf7ce3e9b2d033ca87e272b228257deb69  
**Gap CSV SHA-256:** 8b1191f0bf2096f2fea6f65426866614d7455fdf7279a9d3ea88fd7224935efd

## Cross-source overlap

| Measure | Count |
|---|---:|
| Source gap rows | 4,762 |
| SMC source gap rows | 3,077 |
| History Starter source gap rows | 1,685 |
| Unique symbol-date keys | 3,122 |
| Keys absent in both archives | 1,640 |
| SMC-only gap keys | 1,437 |
| History-Starter-only gap keys | 45 |

The source-row total is larger than the unique key count because the 1,640 shared gaps appear once in each archive.

## Largest symbol concentrations

| Symbol | Source gap rows |
|---|---:|
| NLO | 1,088 |
| AHPC | 557 |
| BNL | 446 |
| SKBBL | 443 |
| UNL | 140 |
| API | 128 |
| CHL | 103 |
| PFL | 96 |
| SLBSL | 96 |
| GBLBS | 86 |

## Largest date concentrations

| Date | Unique symbol gaps |
|---|---:|
| 2026-07-24 | 533 |
| 2026-03-01 | 500 |
| 2026-04-29 | 126 |
| 2025-09-18 | 50 |
| 2026-04-28 | 48 |
| 2026-04-27 | 44 |
| 2026-04-24 | 38 |
| 2026-03-09 | 18 |

## Interpretation and controls

- A gap in both archives is a shared absence, not proof of no trade.
- A one-source gap is a source-coverage difference, not proof that the other source is authoritative.
- The large concentrations require lifecycle, suspension, no-trade and source-omission evidence before adjudication.
- All gap rows remain UNCLASSIFIED_NO_TRADE_OR_MISSING_OR_LIFECYCLE.
- No raw OHLCV or calendar rows were changed; no gap was synthesized, repaired, promoted or admitted to training.
- The overlap report is descriptive and does not close Issue #5.

The reproducible script is scripts/summarize_issue5_cross_source_gap_overlap.py; focused tests validate source identity, canonical dates, duplicate keys and no-promotion controls. Its CI workflow runs the focused tests independently of cross-run artifact credentials.
