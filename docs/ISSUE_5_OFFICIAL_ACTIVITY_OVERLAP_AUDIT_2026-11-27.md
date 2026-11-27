# Issue #5 — official positive-activity overlap audit (2026-11-27)

## Outcome

**Partial primary evidence recovered; the 616-date session calendar remains incomplete.** This is a read-only evidence audit. It does not modify the canonical calendar, raw OHLCV, or repeated-candidate rows, and it does not promote dates.

## Pinned inputs

| Input | Immutable reference | Content identity |
|---|---|---|
| 616 date candidates | `srijankarki07/nepse-data@e6e6fe77cd3378204c7938e66601cee2339a8b7a` | Project cross-check CSV blob `8affc12783c318a552119844fd6bc70bf837ea53` |
| Candidate/index date cross-check | `socrateai-official/nepse-open-data@f602a5b61e68582d28834d16f71151a4bae98d5b` | Project cross-check CSV blob `b63ff7042277a2ffa5ae2277d4bf7910ed836c1d` |
| Official NEPSE market-summary capture | `https://nepalstock.com.np/api/nots/market-summary-history` | Raw response SHA-256 `74165b75b936a920f83ee1d3dc21955a50ef1afaac43e569c719d79d665fb95f`; 31,150 bytes; HTTP 200 |
| Official summary parsed response | Captured 2026-11-26T16:00:20.300521Z | Git blob `aa815aad3a4433f8330bb86be6569dbfa4fe5300` |
| Official summary capture report | Same capture | Git blob `5d864a906df74b0e948c5f9c8e486f795a21fd68` |
| Existing canonical session calendar | `data/reference/nepse_session_calendar.csv` | Git blob `8d50de83ffebe7fba54d3f853087984161c5f8cb` |
| Official holiday API 2024/2025/2026 parsed captures | Annual NEPSE API captures | Git blobs `11cc87afa48a317877c7178646e87c74615ce765`, `8bfecadb8b400c89324e52a342dbad539a78cd57`, `22746b9ee8a2c36e49372e71786c8fa8e7a99ed9` |

## Recomputed overlap

The 616 candidate file contains 616 unique dates from 2024-03-04 through 2026-11-20. The pinned official market-summary response contains 229 unique dates from 2025-11-26 through 2026-11-26. All 229 records have positive turnover, traded shares, transaction count and traded-scrip count; the payload has zero duplicate dates and zero invalid date rows.

| Candidate year | Candidate dates | With official positive-activity summary | Without summary in this capture |
|---|---:|---:|---:|
| 2024 | 189 | 0 | 189 |
| 2025 | 225 | 23 | 202 |
| 2026 (through Nov 20) | 202 | 202 | 0 |
| **Total** | **616** | **225** | **391** |

Four official market-summary dates fall outside the candidate window (2026-11-23 through 2026-11-26). They are not included in the 225 overlap count.

The 225 date matches are direct positive-activity observations in a raw response from the official NEPSE host. They are strong evidence that market activity occurred on those dates. They do not establish a complete 616-session calendar, nor do they prove per-security eligibility or historical data availability at the original decision time.

## Cross-checks and limitations

- The 2024–2026 official NEPSE holiday API captures contain 124 unique date keys. None overlaps the 616 candidate dates. Holiday-list absence is not evidence that a date was open.
- The current canonical calendar contains 41 unique 2026 closure records: 40 `verified_closed` and one `verified_exceptional_closed`. None conflicts by date with the 225 positive-activity summary observations.
- The separate SocrateAI index archive has date files for 614/616 candidate dates. Its two missing date files are 2025-04-03 and 2026-11-20. File presence is not an official session attestation, and this archive's upstream independence is not established.
- The candidate date set originates from a ShareSansar-derived EOD archive. Its date filenames are candidates, not primary session evidence.
- The NEPSE capture report explicitly sets `calendar_claims_promoted=false` and `canonical_calendar_promotion_allowed=false`. This audit respects that boundary.

## Decision

- **Issue #5 join implementation:** already present in draft PR #198. Exact head `c65f8e8c25e863f853b3790601129bfd1cbd9443` passed the focused session-evidence join workflow (run `46040529755`) and backend tests (run `46040529767`).
- **Primary activity evidence:** 225/616 candidate dates now have a pinned official positive-activity summary match.
- **Full 616-date calendar:** still blocked; 391 candidate dates are not covered by this one-year summary capture.
- **Canonical promotion:** none. No calendar row, OHLCV row, repeated-candidate disposition, or training/backtest eligibility was changed.

## Next acceptance step

Acquire an official NEPSE historical market-summary/session register covering the remaining period, especially 2024-03-04 through 2025-11-25, or obtain equivalent date-specific first-party records. Preserve raw bytes, request/response metadata, hashes, scope and availability timestamps. Then independently review the 225 positive-activity claims and rerun the Issue #5 join against an explicitly approved calendar evidence set. Do not classify missing summary dates as closed or open.
