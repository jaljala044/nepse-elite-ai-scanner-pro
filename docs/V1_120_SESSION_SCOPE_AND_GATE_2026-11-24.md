# V1 recent-history scope and acceptance gate — 2026-11-24

## Release decision

App V1 is limited to the latest **120 verified NEPSE trading sessions**. A later version may expand reliable history to a maximum of 2–3 years. The 2–3-year target is not a V1 release blocker.

“120 sessions” means 120 exchange-confirmed sessions, not 120 calendar dates, 120 CSV rows, or 120 dates inferred from one ticker file.

## Snapshot date and current-session handling

The NEPSE website showed the market **open on 2026-11-24 at 1:23 PM** when checked. That is an in-progress session, not a completed EOD bar. V1's historical daily OHLCV cutoff must therefore be the latest fully closed session for which end-of-day data has been published and independently checked. Do not mix an intraday snapshot into a completed daily candle.

Official live page: https://nepalstock.com.np/

## Repository evidence checked

The following default-branch files were fetched and inspected on 2026-11-24:

| Repository/file | Blob SHA | Observed latest date | Notes |
|---|---|---:|---|
| `jaljala044/nepse-smc-data/03_stock_charts_ohlcv/API_OHLCV.csv` | `0e6a37baea92f4f0032980a46773d50b5f41c56c` | 2026-11-19 | 2,520 dated rows; the last 120 distinct file dates span 2026-05-13 through 2026-11-19. No OHLC range violations found in this sample window. |
| `jaljala044/nepse-smc-data/03_stock_charts_ohlcv/AHPC_OHLCV.csv` | `8adf41de96954d38e42f6353cb24a105d3e51082` | 2026-11-19 | 3,780 dated rows; the last 120 distinct file dates span 2026-05-13 through 2026-11-19. No OHLC range violations found in this sample window. |
| `jaljala044/nepse-history-starter/03_stock_charts_ohlcv/API_OHLCV.csv` | `65ebab9f040ff03d42898ae8d80952683b124ad7` | 2026-11-20 | 935 dated rows; the last 120 distinct file dates span 2026-05-30 through 2026-11-20. Contains repeated weekend/carry-forward dates and is not a valid session calendar. |

These are **sample-file findings only**, not a full 525-symbol V1 audit. The different date coverage and end dates demonstrate that neither archive can be treated as a verified, complete session calendar.

The scanner repository's `data/reference/nepse_session_calendar.csv` currently contains only its header:

```csv
date,status,source_id,evidence_uri,verified_at_utc,notes
```

Consequently, there are currently zero exchange-verified session rows in that file. The 2026-05-13 date is a **sample-derived candidate boundary only**, not an approved V1 start date.

## Known wider-history audit is out of scope for this release gate

The previous all-history audit found 1,331 invalid OHLC rows in `nepse-smc-data` and eight source conflicts across the full archive. That audit did not isolate the latest 120 exchange-verified sessions. Do not carry the all-history count into the V1 recent-window result. Recompute all anomaly and conflict counts only after the session window is verified.

The previous audit report remains at:
https://github.com/jaljala044/nepse-elite-ai-scanner-pro/blob/main/docs/HISTORICAL_OHLCV_AUDIT_2026-11-24.md

## V1 acceptance gates

1. **Freeze the as-of cutoff:** use the latest completed EOD session, never a still-open session.
2. **Verify 120 session dates:** populate the calendar from NEPSE notices/official market evidence. Record source URL or document, retrieval timestamp, and verification note for every session. Treat secondary calendars as leads, not authority.
3. **Audit every stock file in the V1 window:** parse all 525 ticker files (or the current verified security universe), preserving raw files and source hashes. Report missing symbols/dates separately from non-traded securities.
4. **Validate OHLCV:** check numeric parsing, positive/zero-volume policy, `low <= open/close <= high`, `low <= high`, duplicate keys, ordering, and plausible volume/turnover. Do not automatically repair.
5. **Reconcile source conflicts:** compare overlapping records to an authorized exchange-origin or licensed source where available. Keep source-specific versions and quarantine unresolved conflicts.
6. **Classify carry-forward rows:** only the verified session calendar can distinguish a non-session carry-forward from a genuine unchanged candle.
7. **Point-in-time provenance:** retain source, source file/hash, observed session date, retrieval/ingestion timestamps, publication/availability timestamp when known, and adjustment basis.
8. **Promote only accepted rows:** quarantined/unverified rows remain available for review but are excluded from canonical V1 analytics.

## Current status

- [x] V1 scope fixed at 120 verified sessions; 2–3 years deferred.
- [x] Confirmed the current NEPSE session was still open at the 2026-11-24 website check.
- [x] Inspected two SMC sample files and one History Starter sample file; calculated sample-only last-120-date windows and OHLC range checks.
- [x] Confirmed the scanner session-calendar CSV is empty apart from its header.
- [ ] Obtain/verify the 120 official session dates.
- [ ] Run full-window audit across all ticker files and market/sector index files.
- [ ] Reconcile recent source conflicts and classify carry-forward rows.
- [ ] Build canonical V1 tables, immutable manifest, and quarantine register.
- [ ] Pass independent QA and publish V1.

**Release status: BLOCKED — not yet eligible for canonical V1 promotion.** The immediate blocker is not the deferred 2–3-year history. It is the absence of a populated, evidence-backed 120-session exchange calendar and a full-window, all-symbol audit.

## Safety rule

No raw source row may be overwritten, silently corrected, or discarded. Any proposed correction must cite authoritative evidence for the corrected value and retain the original value, source hash, reason, reviewer, and timestamp.
