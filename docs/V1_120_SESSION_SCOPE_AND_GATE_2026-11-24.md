# V1 historical-data scope and acceptance gate — 2026-11-24

## Release decision

App V1 will target **one year of reliable NEPSE historical data first**. If a full one-year window cannot pass the data-quality and provenance gates, reduce the V1 historical window to **six months**, provided that six-month window passes. The 2–3-year expansion is deferred to a later app version and is not a V1 blocker.

“One year” and “six months” mean elapsed calendar periods ending at the latest fully closed session, with the included dates determined by an evidence-backed NEPSE session calendar. They do not mean 365 or 180 calendar rows, nor an assumed number of sessions.

The V1 window is a common target for:
- market-wide index and sector history;
- individual stock OHLCV history;
- broker/floorsheet participation history where independently available.

Coverage can differ by data family. Missing broker history must be reported separately; it must not be fabricated or silently substituted with OHLCV.

## Trading calendar regime change

NEPSE changed its weekly trading schedule in April 2026. Reporting on the NEPSE notice says the exchange moved to Monday–Friday trading effective 6 April 2026; previously the regular schedule was Sunday–Thursday. The date-specific calendar must therefore apply the appropriate regime on either side of the change and record exceptional exchange closures/openings separately.

References:
- NEPSE schedule change notice reported 8 April 2026: https://english.ratopati.com/story/57946/stock-market-now-trades-from-monday-to-friday
- NEPSE board decision effective 6 April 2026, reported 6 April 2026: https://english.ratopati.com/story/57517/stock-trading-closed-on-saturday-and-sunday-open-on-friday
- NEPSE schedule change, 8 April 2026: https://thehimalayantimes.com/business/nepse-shifts-to-mondayfriday-trading-week

These reports are secondary evidence of the change, not a substitute for retaining the underlying NEPSE notice itself in the evidence register. Do not infer a session solely from weekday rules: NEPSE may declare additional holidays or special sessions.

## Snapshot date and current-session handling

The NEPSE website showed the market open on 2026-11-24 at 1:23 PM when checked. That is an in-progress session, not a completed EOD bar. V1's historical daily OHLCV cutoff must therefore be the latest fully closed session for which end-of-day data has been published and independently checked. Do not mix an intraday snapshot into a completed daily candle.

Official live page: https://nepalstock.com.np/

## Repository evidence checked

The following default-branch files were fetched and inspected on 2026-11-24:

| Repository/file | Blob SHA | Observed latest date | Notes |
|---|---|---:|---|
| `jaljala044/nepse-smc-data/03_stock_charts_ohlcv/API_OHLCV.csv` | `0e6a37baea92f4f0032980a46773d50b5f41c56c` | 2026-11-19 | 2,520 dated rows; sample file's trailing one-year coverage has not yet been audited. |
| `jaljala044/nepse-smc-data/03_stock_charts_ohlcv/AHPC_OHLCV.csv` | `8adf41de96954d38e42f6353cb24a105d3e51082` | 2026-11-19 | 3,780 dated rows; sample file's trailing one-year coverage has not yet been audited. |
| `jaljala044/nepse-history-starter/03_stock_charts_ohlcv/API_OHLCV.csv` | `65ebab9f040ff03d42898ae8d80952683b124ad7` | 2026-11-20 | 935 dated rows; contains repeated weekend/carry-forward dates and is not a valid session calendar. |

These are sample-file findings only, not a full 525-symbol V1 audit. The differing date coverage and end dates demonstrate that neither archive can be treated as a verified, complete session calendar.

The scanner repository's `data/reference/nepse_session_calendar.csv` currently contains only its header:

```csv
date,status,source_id,evidence_uri,verified_at_utc,notes
```

Consequently, there are currently zero exchange-verified session rows in that file. No official one-year start/end session boundary has yet been approved.

## Recent-window anomaly scope

The previous all-history audit found 1,331 invalid OHLC rows in `nepse-smc-data` and eight source conflicts across the full archive. Those counts must **not** be represented as one-year or six-month V1 findings. Recompute anomaly and conflict counts strictly inside the selected candidate window after the calendar is verified.

Do not spend V1 effort on 2009 rows. They are outside the agreed release window.

The previous audit report remains at:
https://github.com/jaljala044/nepse-elite-ai-scanner-pro/blob/main/docs/HISTORICAL_OHLCV_AUDIT_2026-11-24.md

## V1 acceptance gates

1. **Freeze the as-of cutoff:** use the latest completed EOD session, never a still-open session.
2. **Build a rolling one-year candidate window:** anchored to that cutoff. Derive eligible sessions from date-specific NEPSE notices/official market evidence; use weekday regime only as a cross-check.
3. **Audit every available stock file:** parse the complete current security universe and all ticker files within the candidate window. Report listing lifecycle, IPO/listing date, delisting/suspension where relevant, non-traded days, and missing records separately.
4. **Validate OHLCV:** numeric parsing, positive/zero-volume policy, `low <= open/close <= high`, `low <= high`, duplicate keys, ordering, and plausible volume/turnover. No automatic repairs.
5. **Reconcile source conflicts:** compare overlapping records to an authorized exchange-origin or licensed source where available. Preserve source-specific versions and quarantine unresolved conflicts.
6. **Classify carry-forward rows:** use the verified session calendar plus security trading status to distinguish non-session carry-forward from genuine unchanged candles and non-trading securities.
7. **Audit market and sector data:** validate index/sector dates, OHLC relationships, breadth/turnover fields and completeness for the same calendar window.
8. **Audit broker/floorsheet coverage separately:** record page/contract counts, completeness indicators, source provenance and known limitations. Broker codes are identifiers, not evidence of beneficial ownership or intent.
9. **Point-in-time provenance:** retain source, source file/hash, observed session date, retrieval/ingestion timestamps, publication/availability timestamp when known, and adjustment basis.
10. **Choose release window by evidence:** if the one-year window passes the required gates, use it. If it does not, document exact blockers and evaluate six months. Use six months only if it independently passes. If neither passes, do not label the dataset verified or release it as canonical.
11. **Promote only accepted rows:** quarantined/unverified rows remain available for review but are excluded from canonical V1 analytics.

## Current status

- [x] V1 priority changed from 120 sessions to one year first, six months fallback.
- [x] 2–3-year expansion deferred to a later version.
- [x] Identified April 2026 weekday regime change (Sunday–Thursday to Monday–Friday); calendar logic must be date-aware.
- [x] Confirmed current sample files have inconsistent coverage and the History Starter API file includes weekend/carry-forward rows.
- [x] Confirmed scanner session-calendar CSV is empty apart from its header.
- [ ] Capture and verify the NEPSE primary notice for the April 2026 schedule change.
- [ ] Populate evidence-backed session calendar for the candidate one-year window.
- [ ] Run full-window audit across all ticker files and market/sector index files.
- [ ] Reconcile recent source conflicts and classify carry-forward rows.
- [ ] Audit floorsheet/broker-flow coverage and completeness for the same period.
- [ ] If one year fails, repeat acceptance assessment on six months.
- [ ] Build canonical V1 tables, immutable manifest, and quarantine register.
- [ ] Pass independent QA and publish V1.

**Release status: BLOCKED — not yet eligible for canonical V1 promotion.** The current blocker is an evidence-backed session calendar and complete one-year all-symbol audit, not the deferred 2–3-year expansion.

## Safety rule

No raw source row may be overwritten, silently corrected, or discarded. Any proposed correction must cite authoritative evidence for the corrected value and retain the original value, source hash, reason, reviewer, and timestamp.
