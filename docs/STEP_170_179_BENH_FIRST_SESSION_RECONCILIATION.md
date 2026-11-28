# Steps 170–179 — BENH 14/15 October first-session reconciliation

## Ten-step evidence and implementation batch
1. Rechecked PR #298: open draft, unmerged; both backend tests and backend contract tests passed on exact head `372ff6e5dfc56a67d297854d48b21e9c5467d6c0`.
2. Retrieved the complete public 14-Oct 2026 daily CSV from the archive's raw GitHub URL.
3. Retrieved the complete public 15-Oct 2026 daily CSV from the same archive.
4. Retained both source responses under `data/evidence/benh/2026-11-28/public_daily_csv/`.
5. Parsed the 14-Oct file: 354 data rows; no BENH row.
6. Parsed the 15-Oct file: 349 data rows; BENH is row 17.
7. Extracted BENH 15-Oct OHLCV: 273 / 313.90 / 273 / 313.90; volume 90; turnover Rs26,634; 9 transactions; VWAP 295.93.
8. Cross-checked 15-Oct close 313.90 and volume 90 against NEPSE's public stockWisePrices page; values match.
9. Added integration tests against the retained CSV files to prevent regressions in the 14-Oct absence / 15-Oct presence finding.
10. Recorded source provenance, caveats, listing context and the distinction between first-observed and first-ever trade dates.

## Finding
**First observed BENH trading session in the retained third-party daily archive: 15 October 2026.**

The 14-Oct daily CSV contains 354 securities and no BENH row. ShareSansar's BENH listing page reports listing on 13-Oct and scheduled trading commencement on 14-Oct. The next day's BENH row matches NEPSE's public stockWisePrices close and volume. This is consistent with BENH not having a recorded trade on 14-Oct and first trading on 15-Oct, but the 14-Oct absence remains provisional: a complete exchange-native BENH floorsheet or equivalent primary no-trade evidence is still required to certify the first-ever trade date.

## Source evidence
- 14-Oct raw CSV: https://raw.githubusercontent.com/OmitNomis/ShareSansarScraper/master/docs/Data/2026_10_14.csv
- 15-Oct raw CSV: https://raw.githubusercontent.com/OmitNomis/ShareSansarScraper/master/docs/Data/2026_10_15.csv
- NEPSE stockWisePrices: https://www.nepalstock.com/stockWisePrices
- ShareSansar BENH listing context: https://www.sharesansar.com/company/benh
- Archive README/provenance: https://github.com/OmitNomis/ShareSansarScraper

## Data quality and safeguards
- Source class: unofficial third-party archive, disclosed as derived from ShareSansar daily price table.
- 15-Oct close and volume independently match NEPSE public data.
- 14-Oct no-row result is not promoted to a confirmed exchange no-trade assertion.
- Data quality: MEDIUM for research.
- First-ever trade date: NOT FULLY VERIFIED.
- Production admission: NO.
- SHA-256: not computed; no digest claim is made.
