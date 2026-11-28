# Steps 150–159 — public BENH history archive import

## Ten completed implementation steps
1. Rechecked PR #296 exact head and both CI workflows before starting this batch.
2. Located the public ShareSansarScraper archive and its public JSON API.
3. Read the archive metadata: last updated 2026-11-27; 942 archived trading days; 525 symbols; 353 symbols in latest session.
4. Read the BENH compact history endpoint directly and retained its exact JSON response as a source-evidence snapshot.
5. Added a parser for the archive's declared compact columns: date, OHLC, LTP, VWAP, volume, turnover and change percentage.
6. Added chronological, duplicate-session, schema, numeric and OHLC relationship validation.
7. Normalized each row with source URL, retrieval timestamp, unofficial third-party source class and research-only status.
8. Explicitly prevented missing BENH rows from being interpreted as proof of zero market trades or non-trading sessions.
9. Cross-checked the 27 Nov record against Sun Securities' independently rendered BENH history: O/H/L/C 800/840/771/785; volume 33,244. The values match the archive.
10. Added tests for 22-row import, 14-Oct chronology boundary, duplicate rows, invalid OHLC and reordered schema.

## Exact public evidence
- Archive BENH history: https://omitnomis.github.io/ShareSansarScraper/api/history/BENH.json
- Archive metadata: https://omitnomis.github.io/ShareSansarScraper/api/meta.json
- Archive schema/manifest: https://omitnomis.github.io/ShareSansarScraper/api/index.json
- Archive project and source disclosure: https://github.com/OmitNomis/ShareSansarScraper
- Independent price-history cross-check: https://sunsecurities.com/company/BENH/price-history

## What the snapshot contains
22 BENH session rows, from 2026-10-15 through 2026-11-27. The archive's symbol-history is sparse: it contains dates on which the symbol appears in the daily source table. It does not prove that every omitted calendar/trading session had zero trading, nor does it prove absence on 2026-10-14. A complete dated market-wide CSV/floorsheet is still needed for that conclusion.

## Data quality and admission
- Provenance: public GitHub Pages JSON archive; archive README says data is sourced from ShareSansar and is unofficial/not affiliated with NEPSE.
- Capture: direct public JSON response, stored unchanged as a snapshot.
- Quality: MEDIUM for research use; source is third-party, not exchange-native.
- Production admission: NO. Requires cross-source reconciliation, original source-session evidence, effective-dated identity and corporate-action checks, and independent primary exchange evidence where needed.
- Do not infer the first-ever trade date from the first row in a sparse symbol-history file.
