# 3B.01 — Official one-year history audit

**Capture window:** 2025-11-26 through 2026-11-25  
**Audit run:** [GitHub Actions run 45897905394](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45897905394)  
**Status:** review-only; canonical promotion and production eligibility remain disabled.

## Capture scope and integrity

The workflow queried the official NEPSE per-security history endpoint for the 281 current ordinary-equity candidates in the pinned project crosswalk. It also checked the official market-summary-history capture for the same date window.

| Measure | Result |
|---|---:|
| Current equity candidates | 281 |
| Verified current security-ID crosswalk matches | 281 / 281 |
| Official market-summary session dates in window | 228 |
| Official per-security HTTP 200 responses | 281 / 281 |
| Per-security history rows | 61,665 |
| Distinct symbol/session keys | 61,665 |
| Duplicate symbol/session keys | 0 |
| Explicit zero-volume rows | 474 |
| Active rows (volume > 0) | 61,191 |
| Active rows with invalid H/L/C bounds or nonpositive prices | 0 |
| Raw response and manifest files hash-verified | 282 / 282 |

The capture report and every per-security raw response are retained under
`data/evidence/raw/nepse/security-history/2025-11-26_to_2026-11-25/`.
The workflow also uploaded a 90-day artifact. The audit is reproducible from
the pinned source capture, crosswalk, lifecycle input, and official
market-summary response.

## Observation coverage for the signal engine

The history endpoint returns high, low, close, traded quantity, turnover and
trade count. It does **not** return opening price. The signal-confirmation
classifier itself consumes high, low, close and volume, not open; its input
validator was therefore separated from the broader scanner's full-OHLCV
validator. This does not weaken the production eligibility gate.

Zero-volume rows are explicit no-activity records, not active price
observations. The classifier now excludes them from the 55-observation
minimum, moving averages, breakout lookback and relative-volume baseline.
Three of the 474 zero-volume rows also have zero high/low/close values; they
are excluded with the other no-trade rows rather than treated as prices.

| Coverage measure | Result |
|---|---:|
| Securities with at least 55 active-volume observations | 279 / 281 |
| BENH active-volume observations | 20 |
| NLO active-volume observations | 7 |
| Zero-volume rows excluded from signal observations | 474 |

The two low-activity securities remain insufficient for the default signal
classifier. A 228-row date count must not be confused with 228 active
observations for every security.

## Missing-date reconciliation

The 228-date audit reports 2,403 symbol/date pairs before the lifecycle
register's `valid_from` dates and **zero unexplained missing pairs** inside
this bounded window. The lifecycle register currently uses secondary
listing/first-trade evidence for 44 symbols and has no dated start evidence
for 237; secondary context does not prove historical security identity.

A separate request through 2026-11-26 showed why the bound matters: the
official market-summary archive reports activity on 2026-11-26, but all 281
per-security history responses ended at 2026-11-25. Those 281 missing rows
are an unresolved final-session publication/availability gap, not zero-trade
evidence. They are excluded from the completed-window coverage result and
remain explicitly unresolved for 2026-11-26.

## Acceptance blockers

The capture is official-origin evidence, but it is not yet canonical reviewed
data. The audit deliberately leaves these controls false:

- Historical security identity: current symbol/ID matches do not prove the
  same security ID applied throughout the historical window.
- Official session calendar: market-summary dates are evidence of reported
  sessions, but a separately verified official calendar is not yet admitted.
- Per-security completeness: the lifecycle dates are secondary/contextual,
  and the latest session publication gap remains unresolved.
- Full market universe: 281 ordinary-equity candidates are not all 573
  securities/instruments in the captured current security list.
- Source rights and source independence: written retention/reuse rights and
  independent-source status have not been established.
- Corporate-action treatment: split, bonus, rights and other adjustment
  methodology has not been certified.

Accordingly, `historical_security_identity_verified`,
`official_session_calendar_verified`, `per_security_completeness_verified`,
`source_independence_verified`, `source_rights_verified`,
`coverage_admission_allowed` and `canonical_promotion_allowed` remain
false. No captured rows were added to the canonical reviewed-row manifest.
No backtest or production signal is claimed.

## Code and test changes

- Signal confirmation validates only the H/L/C/volume fields it actually
  consumes, so it does not invent or require an opening price.
- Zero-volume records are excluded from the signal observation count and
  technical calculations.
- The server-side source/session/point-in-time eligibility gate remains
  unchanged and fail-closed.
- Added tests for official-history rows without open and for exclusion of
  zero-volume records.
- Fixed a regression in the separate Srijan public-archive comparator caused
  by accidentally applying SocrateAI discrepancy-statistics code to it.

The complete-window capture workflow and its tests passed in run
[45897905394](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45897905394).
Latest backend/contract CI for the later comparator fix passed in run
[45898263009](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45898263009)
and [45898262972](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45898262972).
The signal-validator and zero-volume tests passed on code commit
`3c36ed5368d076212bede4e571095dbe46e7dd10`: [backend tests](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45898475384), [contract tests](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45898475337), and [public archive audit](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45898475354) all passed. Later commits only updated documentation and the PR description.

**Decision:** this materially improves the evidence baseline and allows
research code to handle the fields NEPSE actually publishes, but 3B.01 is
still not accepted for production. Keep all data quarantined and do not
advance to 3B.02 yet.
## NEPSE data-use policy check

The project also located NEPSE's own hosted **Data Usage Procedure 2077** PDF
through NEPSE's document endpoint. The procedure describes a formal
application stating the intended use and an agreement before API use. Its
published fee schedule has a category for foreign companies/individuals
requesting research data; the one-year offline historical-data line is USD
700 one-time, and the schedule lists a USD 2,000 one-time installation charge
as mandatory for API users. The document is dated 2077/2022 and the current
fee schedule or its application to the public website endpoint has not been
independently reconfirmed with NEPSE.

This does **not** establish that merely viewing the public website is itself
licensed API access, nor does it settle whether the project's specific
non-commercial use falls under another category. It does mean that public
endpoint accessibility cannot be treated as a blanket free-use or
redistribution grant. Since this task is constrained to freely available
data and no paid access or provider correspondence is authorized, no licence
or API agreement was sought. The rights gate therefore remains false.

Official NEPSE-hosted procedure: [Data Usage Procedure 2077 PDF](https://www.nepalstock.com.np/api/nots/security/fetchFiles?fileLocation=santosh_thapa%2F2022-11-07%2Fdc3c594bb83da088339bda0215515e18_1667801106767.pdf). The fee schedule appears in the section for foreign company/individual research use. The related [ShareSansar notice](https://www.sharesansar.com/index.php/newsdetail/30-day-application-deadline-for-users-who-want-to-use-nepses-api-data-usage-what-are-the-rates-to-get-access-to-api-2022-11-07) summarizes the application and agreement requirement.