# Issue #5 — repeated-row candidate overlap with NEPSE holiday API evidence

Date: 2026-11-27

## Inputs and integrity

| Input | Artifact | SHA-256 |
|---|---:|---|
| Repeated-adjacent candidate archive | 14985599288 | `4b8b7c27c642fee768eb3b031928e785a5ef296dc346b4d5c3b8212ba09def67` |
| NEPSE official holiday API multi-year captures (2015–2025) | 15027700386 | `ce8959b0f185d92c936a0c5e137cb2645b33c5d6d23b1ff38c15e2e1d68b7eec` |
| NEPSE official holiday API 2026 response | repository raw object | `dd1777e3c61623048e00dc170d860659b14b8821ffabff8338002ccafdb2ea8f` |

The repeated-row archive contains 196,784 candidate records. The holiday API captures contain 499 original records over 12 years, representing 498 unique year/date keys; both 2020-04-13 records are retained.

## Join definition

For every repeated-row candidate pair, the analysis checks three date positions against the official holiday API date-key set:

1. `previous_date`
2. `current_date`
3. Calendar dates strictly between the two endpoints

This is a date-key overlap only. It does not use weekday assumptions, holiday descriptions as inferred scopes, or the absence of an API record as proof of an open session.

## Results

| Measure | Candidate rows |
|---|---:|
| Total candidates | 196,784 |
| Previous-date endpoint has API date key | 32,426 |
| Current-date endpoint has API date key | 59,282 |
| Either endpoint has API date key (union) | 74,047 |
| Both endpoints have API date keys | 17,661 |
| At least one intervening date has API date key | 64 |
| Any endpoint or intervening date match (union) | 74,105 |

Union by source:

| Pinned source | Total candidates | Any API date overlap |
|---|---:|---:|
| `nepse-history-starter` | 102,241 | 38,505 |
| `nepse-smc-data` | 94,543 | 35,600 |

Union by current-date year:

| Year | Candidates | Any API date overlap |
|---|---:|---:|
| 2011 | 1 | 0 |
| 2016 | 4 | 0 |
| 2024 | 69,114 | 24,050 |
| 2025 | 84,802 | 34,470 |
| 2026 | 42,863 | 15,585 |

## Interpretation and hard limits

These are **holiday-API date overlaps, not verified closure classifications**:

- All 499 holiday API rows have null `instrumentTypeId` and `activeStatus`; instrument scope is unknown.
- Annual completeness is not established. The 2018 response ends on 2018-11-09 and 2019 ends on 2019-10-30.
- 2020-04-13 has two distinct descriptions and is preserved as two records.
- The 2026 capture was retrieved on 2026-11-25, after the repeated-row archive's last candidate date (2026-11-20); point-in-time availability must be considered before any downstream use.
- The API is closure-only and does not enumerate verified open sessions.
- A candidate whose date overlaps an API holiday row may still be a scope mismatch, a date-key issue, or a data-source defect; the join alone does not determine which.

No candidate is relabelled as a confirmed holiday, non-session, carry-forward, or invalid OHLCV row. No source row is modified, removed, repaired, forward-filled, or promoted. The join is a prioritization queue for date-level NEPSE notice/session verification only.

## Next acceptance gate

Obtain immutable official NEPSE schedule-change notice bytes for the 2022 and 2026 weekly-regime transitions, and acquire primary date-level open-session observations. Reconcile their publication/effective dates, instrument scope, retrieval time and hashes; then rerun the candidate join with explicit statuses. Do not use weekday regimes or API absence to synthesize `verified_open` dates.
