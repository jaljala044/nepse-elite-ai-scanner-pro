# NEPSE P1 investigation log

Last updated: 2026-11-25
Repository: jaljala044/nepse-elite-ai-scanner-pro
Working branch: fix/p1-empty-nepse-responses
Related pull request: #12 (keep draft/open; do not merge without explicit approval)

## Current acceptance state

- Eight OHLCV conflicts remain quarantined.
- Canonical promotion is disabled.
- Training is disabled.
- No conflict is considered fully resolved until primary exchange OHLCV evidence, corporate-action review, and price-basis provenance are all documented.

## Latest committed capture evidence

Latest capture evidence commit previously inspected: `82b898d82b96177e8e31c645c6f057cd1da7a035`.
Workflow: `.github/workflows/capture-nepse-conflict-ohlcv.yml`.
Capture implementation: `backend/capture_nepse_conflict_ohlcv.py`.
Pinned client: `nepse-client==0.1.4`.

Observed results from the latest inspected run/artifact:
- 17 raw responses captured for seven securities.
- Raw responses and SHA-256 checksums are archived by the workflow.
- Security-list and per-security history requests succeeded.
- For API, HRL, and RHGCL on 2026-11-19, the per-security NEPSE history confirms high, low, close, and volume, but does not provide open. These are partial primary corroborations, not complete OHLCV verification.
- For BGWT, MEHL, RAWA, RHGCL, and ULHC on 2025-07-28, the per-security history returned valid empty collections. This is not proof that the securities did not trade.
- Date-specific `today-price` POST returned HTTP 401 for both disputed dates.
- Daily-scrip graph POST returned HTTP 200 with empty-list bodies for the seven securities. Do not infer OHLCV from empty graph responses.
- Previous 2025-07-28 secondary ShareSansar-derived archive rows matched Source A; the 2026-11-19 secondary archive rows matched Source B. This archive is secondary, not primary NEPSE evidence.

## Authentication investigation (new finding)

The capture code calls `NepseClient.getPriceVolumeHistory(business_date=...)`, which constructs a POST request to the configured `todays_price` endpoint with a `businessDate` query parameter and uses the floor-sheet payload-ID generator.

The graph request uses a different POST payload-ID generator (`getPOSTPayloadIDForScrips`). In the same capture session, graph POST returned HTTP 200 while `today-price` returned HTTP 401. This narrows the issue to route-specific access/payload behavior; it does not prove the exact cause.

Public NEPSE-client documentation/source inspected on 2026-11-25 describes distinct payload generators for scrip and floor-sheet requests and a Salter authorization header. The public documentation currently surfaced as v0.1.1 and is not proof of the exact pinned v0.1.4 implementation. Do not copy a newer implementation into the project without verifying the pinned package source and regression tests.

## Next steps

1. Inspect the exact installed `nepse-client==0.1.4` source in a reproducible CI diagnostic job. Record only sanitized method signatures, endpoint path, HTTP status, response headers relevant to diagnosis, and request body shape; never log access tokens, salts, authorization headers, or secrets.
2. Add a safe control probe to a known POST route (for example, the current floor-sheet route with a minimal page/size) in the same client session. Compare status codes and response shape with graph and date-specific `today-price`.
3. Verify how the pinned v0.1.4 floor-sheet payload generator computes its payload ID, and whether the date-specific endpoint's query parameter/payload combination is still accepted. Treat any proposed fix as a hypothesis until an actual 2xx response and raw body are captured.
4. If the route remains 401, document it as access blocked and seek an official NEPSE historical EOD archive/report or written data access route. Do not substitute ShareSansar-derived data as primary.
5. Complete issuer corporate-action lifecycle and price-basis provenance reviews for all eight conflicts.
6. Keep all eight quarantined, promotion disabled, training disabled, and PR #12 unmerged until all acceptance criteria are met.

## Eight disputed records

| Symbol | Date | Source A | Source B |
|---|---|---|---|
| API | 2026-11-19 | 331, 334.2, 330.2, 333, 26717 | 331, 334.2, 330, 331.8, 105340 |
| BGWT | 2025-07-28 | 940, 992, 933.4, 957.17, 14028 | 940, 992, 933.4, 945, 14028 |
| HRL | 2026-11-19 | 483, 488, 480, 486, 18817 | 483, 488, 480, 483.9, 49184 |
| MEHL | 2025-07-28 | 471.1, 480.5, 460, 475.63, 29753 | 471.1, 480.5, 460, 470.83, 29753 |
| RAWA | 2025-07-28 | 796, 811, 780.3, 796.9, 3165 | 796, 811, 780.3, 794.83, 3165 |
| RHGCL | 2025-07-28 | 346.7, 362, 341.4, 357.05, 296715 | 346.7, 362, 341.4, 350.07, 296715 |
| RHGCL | 2026-11-19 | 252.1, 259.5, 252.1, 256, 4216 | 252.1, 259.5, 252.1, 258, 9054 |
| ULHC | 2025-07-28 | 509, 515, 495, 510.75, 32288 | 509, 515, 495, 504, 32288 |

OHLCV ordering above: open, high, low, close, volume.

## 2026-11-25 follow-up: exact v0.1.4 authentication bug and historical archive findings

### Authentication investigation — corrected interpretation of v0.1.4 payload semantics

Inspected the exact published nepse-client==0.1.4 source at tag v0.1.4 (release published 2025-11-12), not the newer v0.1.1 documentation:

- NepseClient.getPriceVolumeHistory(business_date) adds businessDate to the URL and deliberately passes the unbound getPOSTPayloadIDForFloorSheet callback.
- getPOSTPayloadIDForFloorSheet() without an argument derives its ID from the current market-status ID and current day-of-month. The package's market-status function reads the current NEPSE market-open response.
- The newer independent reverse-engineering implementation documents the same current-session formula: lookup-table value + market-open ID + 2 × current day-of-month. This supports treating businessDate as a data filter, not as the authentication clock.
- Therefore the earlier interpretation that v0.1.4 had a bug because it did not pass the historical date into the payload generator was incorrect. The date-bound caller change was only a diagnostic hypothesis and did not resolve the 401; it has now been reverted to the package's current-session payload semantics.

Project changes on fix/p1-empty-nepse-responses:
- The initial helper/test experiment bound historical businessDate into the payload generator; run #8/#9 showed it did not clear 401. That interpretation is superseded by the correction below.
- 510c670790c009bec7d83235c23a6f55c1d81e19: updated the capture workflow to run the focused unit tests and automatically run a capture when relevant files change on this feature branch, while retaining manual workflow_dispatch.

Important: these are code-level and test-fixture changes only. A live NEPSE 2xx response has not yet verified the authentication fix. The capture workflow must complete and the preserved raw response must be inspected before calling the endpoint issue resolved.

### Five older records: archive recovery versus primary proof

Fetched srijankarki07/nepse-data at main, file data/daily/2025/2025-07-28.csv, Git blob SHA 329146bbdb0ef66722933f8aba0542c7e4ec78f8. The file contains all five disputed records and matches Source A exactly:

| Symbol | 2025-07-28 OHLCV from archive | Match |
|---|---|---|
| BGWT | 940, 992, 933.4, 957.17, 14028 | Source A |
| MEHL | 471.1, 480.5, 460, 475.63, 29753 | Source A |
| RAWA | 796, 811, 780.3, 796.9, 3165 | Source A |
| RHGCL | 346.7, 362, 341.4, 357.05, 296715 | Source A |
| ULHC | 509, 515, 495, 510.75, 32288 | Source A |

The archive README documents its backfill route as ShareSansar's POST /ajaxtodayshareprice; the public archive describes itself as scraped from ShareSansar. This is a durable secondary historical copy, not an original NEPSE export. It corroborates Source A but does not satisfy the requested primary-evidence gate. A second public ShareSansar archive was also identified, but it is the same upstream source family and is not independent primary corroboration.

A contemporaneous ShareSansar market recap exists for 2025-07-28, but it reports market-wide totals/index context, not the five individual OHLCV rows. No original NEPSE-issued daily report, exchange CSV, or archived NEPSE response containing these five complete rows has been located in this pass.

### Updated decision

- Endpoint authentication: a specific v0.1.4 payload-date bug is identified and patched; live verification is pending.
- Five 2025 records: historical secondary rows recovered and all match Source A; original NEPSE evidence remains unavailable.
- All eight conflicts remain quarantined. No canonical promotion, no training, and no merge.

### Run #9: date-bound payload did not clear 401; control probe isolates route

Workflow run #9: https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45677289652
Artifact ID: 15053380108
Artifact SHA-256: fd876aba4d67ac6c178ff912be83a48e3c42390e009ee6af0efc9956cf6f914e

- All five focused capture tests passed.
- The corrected historical payload was sent for both 2025-07-28 and 2026-11-19, but both today-price requests still returned HTTP 401 with a two-byte empty-list body. Thus the v0.1.4 date-binding defect is fixed in our caller, but it was not the only cause of the 401.
- A minimal floor-sheet POST control in the same client session returned HTTP 200 (two-byte empty-list body). This shows the session's Salter authorization and at least one floor-sheet POST route are accepted; it narrows the failure to the today-price route or its route-specific request contract. The empty control body is not evidence of a trade.
- The per-security history GETs continued to return data for 2026-11-19 but valid empty collections for the five older 2025 records.
- The evidence artifact uploaded successfully, but the evidence commit push was rejected because the feature branch advanced during the run. Run #9 used the previous workflow version; the new workflow commit adds a same-branch fetch/rebase before push. Recheck this in the next run.

No endpoint authentication pass yet. Do not infer that HTTP 200 on the floor-sheet control fixes today-price. All eight remain quarantined; no training or promotion.


### Correction after run #10: current-session payload is the intended contract

The exact v0.1.4 tag resolves to source commit c84f037e544cee8e4a7d8f7c5add31539d5da54e. Its getPriceVolumeHistory implementation passes getPOSTPayloadIDForFloorSheet without a business_date argument. The current-session payload formula is also described by the independent reverse-engineering project at https://github.com/rajeevpaudel/nepse-api (payload_calc.py and docs/blog.md): fetch market-open id, then calculate lookup[id] + id + 2 × current day-of-month. This independent implementation is not an official NEPSE specification, but it corroborates the library's current-session behavior.

The caller has therefore been corrected back to the package's intended contract. A new regression test asserts that the historical businessDate remains in the URL while the payload generator is called with no historical date argument. A new current-session today-price probe (no businessDate query parameter) is included in the next capture, alongside the historical today-price probes and the minimal floor-sheet control.

Run #10: https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45677312190
- Focused capture tests passed.
- Evidence capture commit succeeded after the same-branch rebase fix: 51dafef (full commit is available in the branch history).
- Both historical today-price requests still returned HTTP 401.
- The floor-sheet control returned HTTP 200 with an empty-list body. This proves route-level acceptance for that control, not data availability.
- The run still failed its evidence-completeness gate. Authentication remains unresolved.

The next diagnostic is the no-businessDate current-session today-price request. If it also returns 401 while the floor-sheet control remains 200, the endpoint is likely independently restricted or requires a different route-specific request contract. Do not change tokens, salts, or payload formulas based on guesswork; compare raw responses and exact source behavior first.

### Run #13: route-wide today-price 401 confirmed

Workflow run #13: https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45677613651
Artifact ID: 15051468437
Artifact SHA-256: 71a53e1f6fca30b6d5be93fc15d472bee91921768ac3070377e19efc7baeccf8

- Focused capture regression tests passed.
- today-price returned HTTP 401 for both historical dates and for a current-session request with no businessDate parameter. All three responses were the same two-byte empty-list body.
- The minimal floor-sheet POST control returned HTTP 200 with a two-byte empty-list body.
- Therefore the issue is not merely historical-date filtering. It is specific to the today-price route/request contract or host/header routing. The floor-sheet 200 control does not prove the today-price route is authenticated.

### Additional July 2025 archive cross-check (not primary proof)

Inspected socrateai-official/nepse-open-data at commit 7648ec7ce9988e032975d6cf8bcc876ba7da7ae5, committed 2025-07-28. Its ohlc_unadjusted_stock/unadj_2025-07-28.csv (blob c6642c2d179b34800b5758ad4225b0861dbf5313) contains all five disputed symbols. Its OHLC values match Source B exactly; volumes are close but not identical for BGWT, RHGCL and ULHC:

| Symbol | Archive OHLCV (open, high, low, close, volume) |
|---|---|
| BGWT | 940, 992, 933.4, 945.0, 14016 |
| MEHL | 471.1, 480.5, 460.0, 470.83, 29753 |
| RAWA | 796, 811, 780.3, 794.83, 3165 |
| RHGCL | 346.7, 362, 341.4, 350.07, 296683 |
| ULHC | 509, 515, 495, 504.0, 32285 |

This is a distinct archive and was committed on the session date, but its README does not document the upstream source. Its public issue #2 explicitly asks the maintainer to clarify whether the OHLCV originates from NEPSE, Nepalytix or another provider, and no answer is recorded. The daily floorsheet file is present in the commit but could not be inspected through the available file reader. Consequently this archive is unverified provenance, not original NEPSE evidence and not sufficient for promotion. Do not silently treat the Source B match as proof of origin.

Also inspected Aabishkar2/nepse-data. Its README and scraper code explicitly identify ShareSansar as the source (including the history endpoint and company ID map), so it is another ShareSansar-derived corroboration of Source A, not independent NEPSE proof.

### Next endpoint diagnostic

The current capture workflow adds two controls:
1. Repeat current-session today-price with the package Authorization and payload ID but omit the explicit Host header.
2. Repeat against https://www.nepalstock.com (the other official host) with a fresh client/token on that same host and no explicit Host header.

This follows the independently documented current NEPSE pipeline behavior: both .com and .com.np are separate API hosts; the pipeline strips the library's explicit Host header; its today-price call uses the current-session floor-sheet payload ID. Results are pending in workflow run #16.

## 2026-11-25/26 follow-up: authentication passed; three November rows now have full primary evidence

### Root cause of the today-price 401

The capture was launched at 2025-11-25 18:46 UTC, which was already 2026-11-26 in Nepal (UTC+05:45). The GitHub runner defaults to UTC. nepse-client 0.1.4 derives the current-session floor-sheet payload ID using date.today(). Before the timezone fix, the payload used the UTC calendar day rather than NEPSE's local day.

The capture now sets TZ=Asia/Kathmandu and calls time.tzset() before importing/initializing the NEPSE client. Run #23 recorded:
- UTC timestamp: 2026-11-25T18:46:12.334761Z
- system date after timezone setup: 2026-11-26
- Nepal date: 2026-11-26
- NEPSE market-status asOf: 2026-11-25T15:00:00
- market-status ID: 80

With the Nepal-local day, the today-price route returned HTTP 200 and 347 records. Four controlled requests also returned HTTP 200: package default on nepalstock.com.np, no explicit Host on nepalstock.com.np, fresh session on www.nepalstock.com, and clean browser-style headers on www.nepalstock.com. The clean-header response was 180,192 bytes. This confirms the authentication issue was the runner timezone mismatch; no token, salt, or secret was changed.

### Full primary EOD evidence recovered for the three 2026-11-19 conflicts

The date-specific NEPSE official today-price response for 2026-11-19 returned 347 records and all five required fields. Raw response SHA-256: 0e58623f2db249e4e2e6bef4056ef888afe1bb6a3d611aec662ebece83be6f05. Git blob: f669d24e6e8d92fc951e1eb0603939f4b6102440. Preserved at:
data/evidence/raw/nepse/conflict-ohlcv/2026-11-25/responses/market-price-volume.2026-11-19.response-body.bin

| Symbol | Official NEPSE OHLCV | Result |
|---|---|---|
| API | 331, 334.2, 330, 331.8, 105340 | exact Source B match |
| HRL | 483, 488, 480, 483.9, 49184 | exact Source B match |
| RHGCL | 252.1, 259.5, 252.1, 258, 9054 | exact Source B match |

The evidence ledger was updated in commit 67fecaf3a940160cbd3ed5d79b16caa38e88fdd7. These three are now classified as primary-verified but remain quarantined pending full corporate-action and price-basis review. No training or canonical promotion.

### The five 2025-07-28 records: original EOD endpoint is outside retention

With authentication fixed, the same official today-price route was tested for 2025-07-28. It returned HTTP 500, 27-byte body: "Searched Date is not valid." The per-security history route also returns valid empty collections for dates outside the observed 365-day window. This is consistent with the independently documented rolling-365-day retention limit. The official endpoint cannot now supply the five complete historical EOD rows.

### New trade-level archive candidate: SocrateAI

Inspected socrateai-official/nepse-open-data commit 7648ec7ce9988e032975d6cf8bcc876ba7da7ae5, committed 2025-07-28T11:22:16Z. Its raw daily floorsheet blob 9c5533626b354d5fefca06d6762d51e0b9beaac6 contains 170,727 transaction rows (10,026,040 bytes), schema transaction,symbol,buyer,seller,quantity,rate,amount,date.

Aggregating the five symbols gives:

| Symbol | Trades | Volume | Full-day VWAP | Source B close |
|---|---:|---:|---:|---:|
| BGWT | 194 | 14028 | 944.9918 | 945 |
| MEHL | 333 | 29753 | 470.8399 | 470.83 |
| RAWA | 74 | 3165 | 794.8381 | 794.83 |
| RHGCL | 1030 | 296715 | 350.0754 | 350.07 |
| ULHC | 300 | 32288 | 504.0059 | 504 |

This is strong trade-level corroboration that Source B's close values are full-day VWAP-like values. The raw floor sheet also reproduces most daily open/high/low/volume values, but BGWT has a one-share 925 transaction below the published 933.4 low, so the raw file must not be treated as a clean EOD OHLC board without trade-type/validity filtering.

Important provenance limitation: the SocrateAI README does not state the upstream source. Its open issue #2 asks the maintainer whether OHLCV comes from NEPSE, Nepalytix or another provider; it has zero comments. The raw file is therefore a third-party archived floor sheet with unverified upstream provenance, not yet acceptable as original NEPSE evidence.

### Closing-price methodology explains why the close fields may differ

NEPSE introduced a weighted-average closing-price rule effective 2025-03-20, using trades in the final 15 minutes (14:45–15:00), then reverted to last-traded-price closing from 2025-09-23. 2025-07-28 falls inside the weighted-average period. Source A's closes may therefore represent the official final-15-minute weighted average, while Source B's closes align with the full-day VWAP computed from the archived floor sheet. This is a plausible explanation, not yet proven: the SocrateAI floor sheet has no trade timestamps, so the final-15-minute VWAP cannot be independently recomputed from it.

References:
- NEPSE weighted-average close implementation: https://www.sharesansar.com/newsdetail/nepse-to-implement-15-minute-weighted-average-closing-price-rule-from-chaitra-07-2025-03-19
- NEPSE reintroduced last-traded-price close: https://www.sharesansar.com/newsdetail/nepse-to-reintroduce-last-traded-price-as-closing-price-from-tuesday-2025-09-21
- SocrateAI provenance question: https://github.com/socrateai-official/nepse-open-data/issues/2

### Evidence commit race correction

Run #23's capture artifact uploaded successfully, but the same-day evidence commit conflicted with run #21 because both wrote identical date-based filenames. The workflow now stores each capture immutably under data/evidence/raw/nepse/conflict-ohlcv/run-GITHUB_RUN_ID/ and copies the updated ledger into that run directory. This preserves every run and prevents same-day overwrite/rebase conflicts. Next run will verify the new layout.

### Current P1 decision

- Endpoint authentication: PASS (Nepal-local timezone fix verified against live NEPSE HTTP 200 responses).
- 2026-11-19 API/HRL/RHGCL: full primary OHLCV confirmed; quarantined pending corporate-action/price-basis review.
- 2025-07-28 BGWT/MEHL/RAWA/RHGCL/ULHC: original NEPSE EOD response unavailable outside the 365-day retention window. ShareSansar archive plus unverified SocrateAI trade-level archive corroborate values/methodology but do not satisfy primary-provenance gate.
- All five older records remain quarantined. No canonical promotion, no training, no PR merge.

### Run #24: immutable evidence commit verified

Workflow run #24: https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45679244595
- Focused capture regression tests: PASS.
- Capture step: PASS.
- Evidence commit: PASS.
- Artifact upload: PASS.
- Final completeness gate: correctly FAILED because the five 2025-07-28 records remain unavailable from the official endpoint.
- Evidence was committed immutably under data/evidence/raw/nepse/conflict-ohlcv/run-45679244595/. Capture report Git blob: 1c68711df49e635340985d256977946f17fe5cb6.
- Runtime clock again showed UTC date 2026-11-25 and Nepal date 2026-11-26. Current-session and all controlled today-price requests returned HTTP 200, 180,192-byte JSON responses.
- 2026-11-19 date-specific response returned HTTP 200 with 347 records; API, HRL and RHGCL matched Source B on all five OHLCV fields.
- 2025-07-28 date-specific response is preserved at data/evidence/raw/nepse/conflict-ohlcv/run-45679244595/responses/market-price-volume.2025-07-28.response-body.bin, Git blob d324c03fce63f26b4c6721a707840389b95a66af. Exact 27-byte response: "Searched Date is not valid."

The run-specific evidence directory includes the ledger snapshot, so each run's state is preserved and later ledger updates cannot rewrite its historical record.

### External path to original 2025 evidence

NEPSE's official FAQ directs requests for other information/data to its Research Branch: research@nepalstock.com.np, extension 125. NEPSE's data-usage procedure allows institutions/researchers/investors to apply for real-time or historical API data, subject to the stated application and fee procedure. This is the verified official route for obtaining an original 2025-07-28 EOD export after the public API's rolling retention window has expired.

A broker TMS manual also documents a "Market Time and Sales History" report that can filter by security and date range and returns trade time, price and quantity. A broker-generated export for 2025-07-28 could provide trade-level evidence and allow independent calculation of the final-15-minute close, but access requires the user's broker TMS login.

The TinyFish browser connector has been suggested as an optional way to navigate an authenticated broker TMS portal if the user connects it. It is not connected yet and no TMS account was accessed.

### Five older records — final evidence status for this pass

The five 2025-07-28 records remain quarantined because the official EOD endpoint refuses the date and the third-party floorsheet archive's upstream provenance is undocumented. The ShareSansar archive and SocrateAI floorsheet are useful corroboration, and the closing-price methodology provides a plausible explanation for Source A vs Source B close differences, but neither satisfies the primary NEPSE evidence gate.

No promotion, no training, and no merge. The next necessary input is an official NEPSE historical EOD export or broker TMS Market Time and Sales History export for 2025-07-28.

### Run #42: company-specific historical floor-sheet API also blocked

Workflow run #42: https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45681502604
- Capture regression tests: PASS.
- Capture: PASS.
- Immutable evidence commit: PASS.
- Artifact upload: PASS.
- Final completeness gate: correctly FAILED only because the five 2025-07-28 records remain unavailable.

The official company-specific floorsheet route from nepse-client v0.1.4 was tested for BGWT on both official hostnames:
- https://nepalstock.com.np/api/nots/security/floorsheet/{securityId}
- https://www.nepalstock.com/api/nots/security/floorsheet/{securityId}

Both returned HTTP 403 from nginx (548-byte identical response body), even after:
- using the requested historical businessDate in the floor-sheet payload ID,
- using clean browser-style headers,
- including Origin, X-Requested-With and Sec-Fetch headers,
- omitting the explicit Host header,
- testing both official hostnames.

Raw 403 response blobs are preserved in run-45681502604 under responses/company-floor.BGWT.*.page-0.response-body.bin. This is a separate route-level access restriction, not the today-price authentication issue.

The old NEPSE PHP routes documented by historical scrapers were also tested and found retired:
- /todaysprice on www.nepalstock.com.np returns the modern SPA shell, not the old daily table.
- /company/transactions/{symbol} returns the modern SPA shell, not historical floorsheet rows.
- /datanepse/previous.php on www.nepalstock.com returns the modern SPA shell, not historical market data.

### Official route to obtain the five older records

NEPSE's published Data Usage Procedure 2077 (signed company-secretary PDF) provides a formal historical-data access route. Its non-commercial educational/research category lists historical data up to 2 years at NPR 10,000 one-time and up to 5 years at NPR 50,000 one-time, with the table marking these free for students; all-years data is NPR 100,000 (NPR 5,000 for students). Its commercial financial-tool/data-distributor category lists up to 3 years at NPR 50,000, up to 5 years at NPR 75,000 and more than 5 years at NPR 100,000. The document's installation fee applies to real-time delayed API data, not historical-only data. This is a 2077 procedure and current rates/eligibility must be confirmed with NEPSE before payment.

NEPSE's FAQ directs requests for other data and informational materials to its Research Branch: research@nepalstock.com.np, extension 125. Official procedure reference: https://content.sharesansar.com/photos/FEB12/Dec%202/API_NEPSE.PDF

For 2025-07-28 (within two years of this investigation date), the Research Branch should be asked for the official daily EOD price board and/or historical time-and-sales/floorsheet export for BGWT, MEHL, RAWA, RHGCL and ULHC, including open, high, low, official close, volume, and the closing-price calculation method used on that date. The request should also ask for the permitted research/commercial category and current fee.

A broker TMS Market Time and Sales History export is an alternative if the user has authorized broker access. It should include trade timestamps, rates and quantities so the final-15-minute weighted-average closing price can be independently recomputed. TinyFish has been suggested but is not connected; no broker account has been accessed.

### Updated blocker

The public today-price route is authenticated and working for dates inside its retention window. The historical company_floorsheet route is blocked by nginx on both official hosts. The old PHP historical pages are retired. No public unauthenticated official NEPSE route remains that can return the July 2025 evidence.

The five older records remain quarantined. We must not promote Source A or Source B based only on secondary archives. No training, no canonical promotion, no merge.


The main conflict ledger was updated in commit 23a313f5303868169f365138c1821093de063456 to preserve the exact 2025-07-28 endpoint failures, raw response paths, SocrateAI trade counts/VWAPs, and the unverified provenance/close-methodology caveats for all five older records.


### Follow-up research: official recovery channel and archive provenance audit

The endpoint-authentication fix remains PASS as recorded above. A further public-source audit did not identify an accessible original NEPSE EOD export for 2025-07-28:

- NEPSE's current official FAQ lists the Research Branch as the contact for other data/statistics/information: research@nepalstock.com.np, extension 125 (https://www.nepalstock.com/faq).
- NEPSE's current homepage separately lists Murahari Parajuli at extension 125 with mparajuli@nepalstock.com (https://www.nepalstock.com.np/). Because the published email domains differ, verify the correct recipient with NEPSE before sending.
- NEPSE's published Data Usage Procedure 2077 describes a formal historical-data application route. The procedure and fees are dated; obtain current written confirmation of eligibility, price and permitted use before any payment (https://content.sharesansar.com/photos/FEB12/Dec%202/API_NEPSE.PDF).
- A separately maintained public archive, srijankarki07/nepse-data, explicitly states that its entire historical EOD archive is scraped from ShareSansar, not directly from NEPSE. It is therefore not an independent primary source (https://github.com/srijankarki07/nepse-data).
- The ShareSansarScraper archive likewise explicitly identifies ShareSansar as its upstream and says it is unofficial/not affiliated with NEPSE (https://omitnomis.github.io/ShareSansarScraper/about.html).
- Public search also surfaced SocrateAI's trade-level archive, but its upstream provenance remains undocumented as already recorded above; it cannot be elevated to NEPSE-primary status merely because its aggregates align with Source B.

A submission-ready request has been added at docs/NEPSE_HISTORICAL_DATA_REQUEST_2025-07-28.md. It asks NEPSE for the official EOD board, time-and-sales/floorsheet, closing-price methodology, provenance/certification, and current historical-data access requirements. It is a draft only and has not been sent.

A broker TMS browser profile is not connected to any signed-in site, and no broker identity/URL or credentials have been supplied. No broker account was accessed. If a broker export is later provided or an authorized session is connected, retain it as a distinct broker-origin source unless NEPSE certifies it.

### Evidence gate after follow-up research

- Endpoint authentication: PASS (Nepal-local date/payload mismatch fixed; successful live NEPSE responses and 2026-11-19 official EOD rows are preserved in run evidence).
- Five 2025-07-28 rows: NOT PASS — original NEPSE-issued/certified data has not been obtained. Public archives are secondary or have unresolved provenance.
- All five remain quarantined; no canonical promotion, no training, no PR merge.
- Next external dependency: receive a verifiable NEPSE Research Branch export/confirmation, or a broker time-and-sales export for corroboration plus NEPSE confirmation of the EOD methodology.


### 2026-11-25 follow-up: requested market sites checked; ShareSansar daily archive recovers all five rows

The user asked for direct checks of Chukul, ShareSansar, ShareHu, and MeroLagani for BGWT, MEHL, RAWA, RHGCL and ULHC on 2025-07-28.

#### ShareSansar-sourced dated daily board recovered

Retrieved the dated CSV:
https://omitnomis.github.io/ShareSansarScraper/Data/2025_07_28.csv

The archive's own README/about page says it scrapes ShareSansar's "today's share price" board, stores daily CSVs, and is unofficial/not affiliated with ShareSansar or NEPSE:
- https://omitnomis.github.io/ShareSansarScraper/
- https://omitnomis.github.io/ShareSansarScraper/about.html

Extracted rows from the exact 2025-07-28 CSV:

| Symbol | Open | High | Low | Close | LTP | VWAP | Volume | Transactions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BGWT | 940.00 | 992.00 | 933.40 | 945.00 | 992.00 | 944.99 | 14,028 | 194 |
| MEHL | 471.10 | 480.50 | 460.00 | 470.83 | 478.00 | 470.84 | 29,753 | 333 |
| RAWA | 796.00 | 811.00 | 780.30 | 794.83 | 798.00 | 794.84 | 3,165 | 74 |
| RHGCL | 346.70 | 362.00 | 341.40 | 350.07 | 362.00 | 350.08 | 296,715 | 1,030 |
| ULHC | 509.00 | 515.00 | 495.00 | 504.00 | 512.00 | 504.01 | 32,288 | 300 |

All five OHLCV rows exactly match Source B. The CSV also separately exposes LTP and VWAP, which is important: for these records, the Close column matches the full-day VWAP to rounding, while LTP is materially different. This provides a plausible data-field explanation for the conflict: Source B is consistent with the ShareSansar archive's Close/VWAP fields; Source A's close values are not this archive's Close values. Do not infer from this alone which field NEPSE officially designated as the session close on 2025-07-28.

This corrects/extends the earlier source audit: the previously inspected srijankarki07/nepse-data ShareSansar-derived daily archive matched Source A, while this separate OmitNomis ShareSansar-scraped daily archive matches Source B. The archives are distinct scrapers and claim the same upstream site, but they do not agree on these five close values. They are not independent exchange-primary evidence. Preserve both datasets and their provenance separately; do not collapse them into a single "ShareSansar value."

The CSV URL was retrieved successfully in this investigation. No immutable raw copy or SHA-256 was added to the repository in this pass, so the public URL and extracted rows are the evidence reference for now.

#### Other requested sites / access outcome

- Chukul: stock-profile URLs for the five symbols were requested, but the public page extractor returned empty content for all five. Search did not surface dated 2025-07-28 OHLCV rows or a publicly documented historical OHLCV endpoint. A search result surfaced a current live-market API only; it is not historical proof.
- MeroLagani: its public Datewise Shareprices page is live and has a date filter, but the page fetched in this pass rendered the current 2026-11-25 board. Search did not return a July 2025 dated row, and no confirmed request parameter/POST contract for historical date retrieval was established. Do not claim MeroLagani independently confirms the five rows.
- ShareHu (sharehu.com): direct fetch returned HTTP 403 and search returned no NEPSE historical data. Search surfaced Share Hub Nepal at sharehubnepal.com, which documents an all-time price-history API, but states that it requires a licensed Data API account, bearer token, and allow-listed server IP. No account or licence is available in this session; no API call was authenticated. This is a possible paid access route, not retrieved evidence.
- Note: sharehub.com is a parked domain, not the Nepal data service. The relevant service found in search is sharehubnepal.com; this may or may not be the site the user intended by "sharehu.com".

#### Updated five-record evidence interpretation

The new ShareSansar-scraped CSV makes Source B the strongest *secondary-board field match* for all five records. It also clarifies why the earlier SocrateAI trade aggregation matched B: the ShareSansar archive Close and VWAP are aligned to full-day VWAP. But because the other ShareSansar-derived archive matched Source A, and because NEPSE's 2025 weighted-close policy may distinguish official close from full-day VWAP/LTP, this does not yet settle the official exchange close definition. Obtain the original NEPSE EOD board or certified historical report and the official close methodology before canonical promotion.

#### Updated decision

- Endpoint authentication: PASS, as previously verified.
- Five 2025-07-28 records: secondary evidence expanded; all five ShareSansarScraper CSV OHLCV rows match Source B exactly. Conflicting ShareSansar-derived archive matches Source A. Primary NEPSE proof and close-field semantics remain NOT PASS.
- All five remain quarantined. No canonical promotion, no training, no PR merge.


### 2026-11-25 follow-up: MeroLagani date-filtered Price History retrieved

A live browser inspection found that each MeroLagani CompanyDetail page has a public Price History tab with a Market Date filter. The filter accepts a single date (MM/DD/YYYY) and submits via ASP.NET WebForms postback. No sign-in was required.

The date 07/28/2025 was queried for three symbols. Each query returned exactly one row, with pagination confirming 1 of 1 records:

| Symbol | Market Date | MeroLagani LTP | % Change | High | Low | Open | Quantity | Turnover |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| BGWT | 2025/07/28 | 957.17 | 0.84 | 992.00 | 933.40 | 940.00 | 14,028 | 13,256,345.00 |
| MEHL | 2025/07/28 | 475.63 | -1.05 | 480.50 | 460.00 | 471.10 | 29,753 | 14,008,898.10 |
| RAWA | 2025/07/28 | 796.90 | -1.64 | 811.00 | 780.30 | 796.00 | 3,165 | 2,515,662.50 |

These three MeroLagani rows match Source A's close values exactly and match Source A's open/high/low/volume values. They do not match the ShareSansarScraper CSV's Close values (Source B). MeroLagani explicitly labels the returned field "Last Trade Price (LTP)". Preserve the exact field label; do not silently relabel LTP as NEPSE's official closing price.

The browser confirmed the MeroLagani Price History UI is publicly accessible and the dated result is directly queryable by stock/date:
- BGWT: https://merolagani.com/CompanyDetail.aspx?symbol=BGWT#0
- MEHL: https://merolagani.com/CompanyDetail.aspx?symbol=MEHL
- RAWA: https://merolagani.com/CompanyDetail.aspx?symbol=RAWA

The other two MeroLagani browser jobs (RHGCL and ULHC) were launched and remain pending at the time of this log update; do not treat them as queried or infer their result.

#### Interpretation update

This is a new independent publisher's dated stock-level historical result, and its LTP field supports Source A for BGWT, MEHL and RAWA. Combined with the previously recovered ShareSansar-sourced daily board whose Close/VWAP supports Source B, the evidence indicates a field-definition conflict, not simply random bad rows:
- MeroLagani's LTP = Source A close for the three queried symbols.
- ShareSansarScraper's Close/VWAP = Source B close for all five.
- A different ShareSansar-derived archive matches Source A for all five.

The three MeroLagani results do not by themselves certify NEPSE's official close methodology. MeroLagani is a secondary publisher and labels its field LTP. NEPSE's 2025 weighted-average closing rule remains relevant; a proper resolution requires confirmation of what the official EOD "close" represented during that period (final-15-minute weighted average versus last traded price), or an original exchange record with the field definition.

#### Current gate

- Secondary dated corroboration now includes MeroLagani LTP for BGWT/MEHL/RAWA (Source A close match).
- MeroLagani RHGCL/ULHC still pending.
- Source A is provisionally better supported if the dataset's intended close field is LTP; Source B is supported if the intended field is full-day VWAP. The schema must state which measure it stores.
- All five remain quarantined until the canonical close-field definition and NEPSE method are confirmed. No training, no promotion, no merge.


#### RHGCL MeroLagani result (additional completed query)

The RHGCL Price History query for 07/28/2025 completed and returned exactly one row:
- LTP 357.05; % change 5.03
- High 362.00; Low 341.40; Open 346.70
- Quantity 296,715; Turnover 103,872,614.40

This matches Source A's RHGCL close, open, high, low and volume exactly. MeroLagani still labels the close-like field LTP.

At this point, MeroLagani date-filtered results for BGWT, MEHL, RAWA and RHGCL all support Source A's LTP field. ULHC query remains pending.


### Final MeroLagani pass: all five 2025-07-28 records queried

The remaining ULHC query completed. Its dated Price History row returned:
- Market Date 2025/07/28
- LTP 510.75; percentage change 0.49
- High 515.00; Low 495.00; Open 509.00
- Quantity 32,288; Turnover 16,273,342.10

Together with the four prior MeroLagani date-filtered queries, all five now have one dated result each. All five LTP values match Source A's close exactly; all five open/high/low/volume values also match Source A exactly:

| Symbol | MeroLagani LTP | Source A close | Source B Close/VWAP | Open | High | Low | Volume |
|---|---:|---:|---:|---:|---:|---:|---:|
| BGWT | 957.17 | 957.17 | 945.00 | 940.00 | 992.00 | 933.40 | 14,028 |
| MEHL | 475.63 | 475.63 | 470.83 | 471.10 | 480.50 | 460.00 | 29,753 |
| RAWA | 796.90 | 796.90 | 794.83 | 796.00 | 811.00 | 780.30 | 3,165 |
| RHGCL | 357.05 | 357.05 | 350.07 | 346.70 | 362.00 | 341.40 | 296,715 |
| ULHC | 510.75 | 510.75 | 504.00 | 509.00 | 515.00 | 495.00 | 32,288 |

MeroLagani result details:
- BGWT: LTP 957.17; % change 0.84; turnover 13,256,345.00.
- MEHL: LTP 475.63; % change -1.05; turnover 14,008,898.10.
- RAWA: LTP 796.90; % change -1.64; turnover 2,515,662.50.
- RHGCL: LTP 357.05; % change 5.03; turnover 103,872,614.40.
- ULHC: LTP 510.75; % change 0.49; turnover 16,273,342.10.

Each browser query returned exactly one record for 2025/07/28. The five company pages:
- https://merolagani.com/CompanyDetail.aspx?symbol=BGWT
- https://merolagani.com/CompanyDetail.aspx?symbol=MEHL
- https://merolagani.com/CompanyDetail.aspx?symbol=RAWA
- https://merolagani.com/CompanyDetail.aspx?symbol=RHGCL
- https://merolagani.com/CompanyDetail.aspx?symbol=ULHC

#### Evidence conclusion and data-field decision

The five disputed close values in Source A are independently corroborated by MeroLagani's dated LTP field. Source A also matches MeroLagani's dated open/high/low/quantity for all five. Source B's values match the ShareSansarScraper daily board's Close/VWAP field, which is distinct from MeroLagani's LTP. Thus the discrepancy is best understood as a close-field semantic mismatch: LTP/last-trade-style field versus full-day VWAP-style field.

For the project's OHLCV schema, the close field should mean the exchange's designated session closing price, not full-day VWAP. On 2025-07-28 NEPSE's weighted-average closing-price rule was in force. MeroLagani's historical field is explicitly labelled LTP and exactly matches Source A, which strongly supports Source A as the practical close candidate, but does not by itself certify that MeroLagani's LTP column is NEPSE's officially designated weighted closing price. The source is a secondary publisher. The original NEPSE EOD export or a written confirmation of the historical field/method is still required to satisfy the project's primary-source provenance gate.

Decision:
- Secondary cross-check: PASS for all five (MeroLagani dated LTP and O/H/L/quantity exactly match Source A).
- Competing full-day VWAP interpretation: documented as a separate measure; do not place it in the OHLCV close field.
- Primary exchange certification / official close-method confirmation: NOT PASS.
- Keep the five quarantined pending primary-source/official-method confirmation. Do not train or promote the rows yet.
- No PR merge.


## 2026-11-25/26: repeat MeroLagani verification and Chukul access attempt

### MeroLagani date-filtered recheck (2025-07-28)

A fresh browser pass opened each company's Price History tab, set Market Date to 07/28/2025, and submitted the query.

Freshly completed rows (one row returned for each):
- BGWT: LTP 957.17; % Change 0.84; High 992.00; Low 933.40; Open 940.00; Qty. 14,028; Turnover 13,256,345.00.
- MEHL: LTP 475.63; % Change -1.05; High 480.50; Low 460.00; Open 471.10; Qty. 29,753; Turnover 14,008,898.10.
- RAWA: LTP 796.90; % Change -1.64; High 811.00; Low 780.30; Open 796.00; Qty. 3,165; Turnover 2,515,662.50.
- RHGCL: LTP 357.05; % Change 5.03; High 362.00; Low 341.40; Open 346.70; Qty. 296,715; Turnover 103,872,614.40.

ULHC's separate repeat browser run failed with a provider-side task error after opening the Price History query. Do not count that failed retry as a fresh result. The previously completed date-filtered MeroLagani verification remains recorded in the evidence ledger: LTP 510.75; % Change 0.49; High 515.00; Low 495.00; Open 509.00; Qty. 32,288; Turnover 16,273,342.10.

All four fresh rows match Source A on LTP, open, high, low, and quantity. The earlier ULHC row also matches Source A. MeroLagani labels its close-like field "LTP"; it is secondary-publisher evidence, not NEPSE primary certification. Keep the five records quarantined.

### Chukul access attempt

Attempted https://chukul.com/ with browser navigation both with and without trailing slash. Both navigations timed out after 30 seconds waiting for page load; screenshot timed out after 45 seconds. The rendered page exposed no DOM, links, or images. A separate public-content fetch returned empty_content for the homepage and /stocks; /stock returned a 404 page. No historical date filter, stock history rows, or API route could be verified for BGWT, MEHL, RAWA, RHGCL, or ULHC. Classification: access_blocked_unverified, not evidence of data absence.

### Decision and next step

- MeroLagani secondary date-filter check: four fresh passes plus the earlier recorded ULHC pass (5/5 total evidence on file).
- Chukul: inaccessible in this pass; no rows acquired.
- Original NEPSE primary EOD response for 2025-07-28 remains outside the observed rolling retention window; the official today-price endpoint returned HTTP 500 "Searched Date is not valid." The historical close-method question therefore remains unresolved.
- Next actionable route is official NEPSE confirmation / licensed historical EOD export, including the definition of the 2025-07-28 closing-price field during the weighted-average closing-price period.
- All five 2025-07-28 records remain quarantined; no canonical promotion, no training, and no PR merge.
