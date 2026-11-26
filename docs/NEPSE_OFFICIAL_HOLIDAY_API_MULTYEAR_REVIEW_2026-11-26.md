# NEPSE official holiday API multi-year evidence review — 2026-11-26

## Outcome

The existing public-source capture provides a substantial primary-source closure-evidence collection, but it is **not** a complete historical session calendar. The API is hosted by NEPSE and the capture workflow preserves response bytes before parsing. The evidence must remain source-specific and point-in-time.

## Acquired evidence inventory

The committed audit manifest `data/evidence/acquired/nepse-holiday-api-multiyear-audit-2015-2026.json` records:

- Endpoint template: `https://nepalstock.com.np/api/nots/holiday/list?year={year}`
- Capture workflow run: [45623107909](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45623107909)
- Artifact ID: `15027700386`
- Artifact ZIP SHA-256: `ce8959b0f185d92c936a0c5e137cb2645b33c5d6d23b1ff38c15e2e1d68b7eec`
- Years captured: 2015–2026 (12 annual requests)
- Parsed records: 499; unique date keys summed within annual files: 498; failed years: 0; all HTTP statuses 200.
- Each annual response has a recorded SHA-256 in the manifest.

Annual record counts: 2015 54; 2016 33; 2017 38; 2018 29; 2019 22; 2020 101; 2021 25; 2022 36; 2023 37; 2024 37; 2025 46; 2026 41.

## Exceptions and limitations

1. **2020-04-13 duplicate date:** two distinct descriptions are present — “As Per Order by SEBON Lockdown” and “New Year Holiday”. Preserve both raw records. Do not silently deduplicate or choose one label.
2. **Annual completeness not established:** the 2018 list ends 2018-11-09 and the 2019 list ends 2019-10-30. The API returning HTTP 200 does not prove a full-year holiday list.
3. **Null scope/status fields:** all 499 rows have `instrumentTypeId=null` and `activeStatus=null`. The endpoint does not expose enough metadata to prove whether every entry is an all-market closure, a segment-specific closure, or the complete set of dates relevant to a given instrument class. Inspect descriptions and cross-check notices before applying broad scope.
4. **Closure-only evidence:** the endpoint lists holidays/closures; it does not enumerate all normal open sessions. Absence from this endpoint is not proof that the exchange traded.
5. **2026 canonical file:** the existing `data/reference/nepse_session_calendar.csv` contains 41 reviewed 2026 API dates, with the same response hash `dd1777e3c61623048e00dc170d860659b14b8821ffabff8338002ccafdb2ea8f`. Do not overwrite this reviewed file with a blind multi-year import.
6. **No look-ahead:** retain original capture/retrieval timestamps and do not treat future-dated holiday records as information available before the capture timestamp.

## Schedule-regime evidence status

- **2022-06-16 transition:** an official NEPSE-hosted one-page notice supports the schedule from Asar 1, 2079: Sunday–Thursday 11:00–15:00 and Friday 11:00–13:00. The visual reinspection corrected the Board decision date to 2079/02/24. The notice's original bytes and SHA-256 have not been preserved in the repository; treat it as located/visually reviewed, not a completed immutable evidence capture.
- **2026-04-06 transition:** ShareSansar reports that NEPSE's Board meeting on 22 Chaitra 2082 approved Monday–Friday trading; Ratopati and The Himalayan Times independently corroborate the effective week/date. ShareSansar says NEPSE issued a public notice, but the original NEPSE notice bytes/official record have not been captured. This remains secondary corroboration, not primary schedule verification.

## Disposition

- Keep the existing 2026 date-specific NEPSE API holiday rows as reviewed closure observations, subject to the existing raw-response/hash evidence.
- Keep 2015–2025 API records in a separate source-evidence layer until annual completeness, duplicate-date semantics and scope are reviewed. In particular, 2018/2019 are incomplete-looking and 2020-04-13 is a two-record date conflict.
- Do not synthesize `verified_open` dates from weekday regimes, absence from the holiday API, public/bank holiday lists, or OHLCV/floorsheet file presence.
- Do not classify the 196,784 repeated-row candidates against weekday rules alone.
- Continue acquisition of date-level official exchange trading evidence (market summaries/index observations plus notices) and capture the 2026-04-08 NEPSE schedule notice and the 2022 PDF as immutable raw bytes with hashes.

## Next execution step

Build a deterministic audit that joins the raw annual API payloads to the source manifest, preserves all records, detects duplicate dates and incomplete year spans, and produces a *review-only* closure-candidate ledger. Then obtain official exchange date-level trading observations to establish open sessions independently. No calendar promotion is authorized by this report.


## Independent artifact-byte verification — 2026-11-26

The workflow artifact was downloaded for this review and checked locally:
- Downloaded ZIP size: 38 KB; SHA-256 exactly matches the manifest: `ce8959b0f185d92c936a0c5e137cb2645b33c5d6d23b1ff38c15e2e1d68b7eec`.
- The artifact contains immutable `response-body.bin`, `parsed-response.json`, `capture-report.json`, `response-headers.json`, `source-url.txt` and `SHA256SUMS` for each year 2015–2025.
- For all 11 annual payloads, raw response bytes independently hash-match both the capture report and per-year SHA256SUMS file.
- Parsing each raw response body independently produces a JSON object exactly equal to the preserved parsed-response.json for all 11 years.
- Raw payload record counts independently reproduce: 2015 54; 2016 33; 2017 38; 2018 29; 2019 22; 2020 101; 2021 25; 2022 36; 2023 37; 2024 37; 2025 46.
- Duplicate-date scan independently reproduces the sole duplicate key: 2020-04-13 (two distinct holiday descriptions).

This confirms the downloaded artifact's byte integrity and raw-to-parsed consistency. It does **not** establish the endpoint's annual completeness, the legal/exchange scope of every holiday row, or actual open-session dates. The separate 2026 response remains the 41-row capture already recorded in the current calendar and its source hash.
