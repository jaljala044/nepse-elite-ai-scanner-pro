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
