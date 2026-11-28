# Steps 160–169 — daily market-wide CSV archive ingestion

## Ten-step work package
1. Rechecked PR #297 and its exact-head CI: backend tests and contract tests both passed; PR remains open/draft/unmerged.
2. Read the public archive's JSON API manifest and metadata.
3. Located the documented raw daily CSV pattern in the archive README.
4. Confirmed public daily CSV content paths for 14 Oct and 15 Oct 2026; a 27 Nov path is present in the archive file index.
5. Confirmed the archive's disclosed lineage: daily CSVs are produced from ShareSansar's daily price table and are unofficial third-party records.
6. Added a generic market-wide CSV parser for the documented header and comma-formatted numeric fields.
7. Added OHLC, nonnegative activity, required-column, session-date and duplicate-symbol validation.
8. Added a symbol lookup result that distinguishes found, absent-from-file and ambiguous duplicate records.
9. Added explicit research-only source lineage and a hard production-admission prohibition.
10. Added regression tests and a machine-readable archive manifest.

## Evidence URLs
- README and daily CSV layout: https://github.com/OmitNomis/ShareSansarScraper
- API schema: https://omitnomis.github.io/ShareSansarScraper/api/index.json
- Metadata: https://omitnomis.github.io/ShareSansarScraper/api/meta.json
- 14 Oct CSV: https://raw.githubusercontent.com/OmitNomis/ShareSansarScraper/master/docs/Data/2026_10_14.csv
- 15 Oct CSV: https://raw.githubusercontent.com/OmitNomis/ShareSansarScraper/master/docs/Data/2026_10_15.csv
- 27 Nov CSV: https://raw.githubusercontent.com/OmitNomis/ShareSansarScraper/master/docs/Data/2026_11_27.csv

## BENH chronology: unresolved point
The public archive's per-symbol history starts on 15 Oct. A complete market-wide CSV exists for 14 Oct, but this batch has not extracted the BENH row (or verified its absence) from that full CSV. Therefore the 14 Oct first-trade question remains OPEN. The 14 Oct CSV proves a market-wide file is available, not that BENH was or was not present. Do not infer a no-trade event from a search result or partial file preview.

## Data policy
Third-party archive data is research-only. Validate each complete raw file, preserve source bytes and retrieval hashes in the capture stage, reconcile symbol rows against NEPSE/ShareSansar/Chukul/ShareHub and other available distributors, and keep production admission blocked until independent source-quality and identity gates pass.
