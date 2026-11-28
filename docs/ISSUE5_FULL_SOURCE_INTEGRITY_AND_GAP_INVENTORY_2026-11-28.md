# Issue #5 — full-source integrity and unclassified session-gap inventory

This follow-up uses the immutable archive-audit artifact from PR #355, which audited both pinned 525-file OHLCV repositories. It adds a reproducible active-equity date-gap inventory using the project research calendar and 281-equity manifest.

## Existing full-source structural results

Artifact: `ohlcv-row-level-exception-ledger`, workflow run `46171839262`, artifact ID `15274540199`.

- ZIP SHA-256: `7b4fbaf618bf4801ad1e61e10e745c55013a371067e052ad7a60f42f82aee3f3`
- Audit JSON SHA-256: `252dd49f7c4e808ab14c7a16db0a825ea2d6f9772608cb09807ed6134d7eaa6d`

| Source | Files audited | Rows | Duplicate dates | Out-of-order transitions | Invalid OHLC rows | Download errors |
|---|---:|---:|---:|---:|---:|---:|
| nepse-smc-data | 525/525 | 314,712 | 0 | 0 | 1,331 | 0 |
| nepse-history-starter | 525/525 | 301,632 | 0 | 0 | 0 | 0 |

Across both sources, the full-source audit records zero duplicate dates, zero out-of-order transitions, zero download errors, 1,331 invalid OHLC rows, and eight cross-source conflicts. The invalid rows and conflicts remain separately quarantined; this report does not resolve or rewrite them.

## New check

The workflow downloads the pinned archive-audit artifact and joins each active equity's valid observed dates to project-accepted open sessions between that file's first and last observed dates. It emits one row per unobserved project-session date, separately for each source.

Every gap is labelled:

`UNCLASSIFIED_NO_TRADE_OR_MISSING_OR_LIFECYCLE`

This is intentionally not called a missing trade. Without independent instrument lifecycle, suspension and no-trade evidence, an absent bar cannot be adjudicated. No row is synthesized.

## Acceptance boundary

- Duplicate-date and source-order checks: **PASS** for both pinned archives according to the source audit.
- Invalid OHLC: **OPEN**, 1,331 records remain quarantined.
- Session-gap inventory: workflow-generated artifact pending.
- Gap adjudication: **OPEN**; no-trade, suspension, lifecycle and source omission require evidence.
- Raw OHLCV mutation, deletion, forward-fill, canonical admission and training promotion: **PROHIBITED**.

The workflow is deterministic and records SHA-256 digests for the audit JSON, session calendar and active-equity manifest used in each run.


## Workflow result — 2026-11-28

The pinned-source gap-inventory workflow completed successfully:
- Workflow run: `46175254564`
- Artifact: `15275292210` (`issue5-full-source-gap-inventory`)
- Artifact ZIP SHA-256: `05c3e20add2a6148eed8b9a8e0824a4fe9d18ed5a89286ecd8f46c3db16ddc1e`
- Calendar: 3,671 rows, including 3,630 `project_accepted_open` sessions
- Active equity universe: 281

| Source | Expected equity/session keys | Observed valid keys | Unclassified gaps | Duplicate dates | Out-of-order transitions | Active equity files missing |
|---|---:|---:|---:|---:|---:|---:|
| nepse-smc-data | 175,468 | 172,391 | 3,077 | 0 | 0 | 0 |
| nepse-history-starter | 155,746 | 154,061 | 1,685 | 0 | 0 | 0 |
| **Total** | **331,214** | **326,452** | **4,762** | **0** | **0** | **0** |

The 4,762 are source-specific unclassified gaps, not 4,762 proven missing trades. They involve 278 distinct equities. A symbol/date gap appears in both repositories for 1,640 keys and in only one repository for 1,482 keys (3,122 unique symbol/date gap keys across the union).

Largest combined source-gap counts:
- NLO 1,088
- AHPC 557
- BNL 446
- SKBBL 443
- UNL 140
- API 128
- CHL 103
- PFL 96
- SLBSL 96
- GBLBS 86

These counts prioritize evidence review; they do not establish that a stock should have traded on each date. No-trade, suspension, listing/lifecycle and source omission must be distinguished before any gap can be adjudicated. No OHLCV row is generated or repaired.
