# BENH first-session CSV row quarantine repair

## Scope

This repair is stacked on PR #299 and does not modify its branch. The retained ShareSansar-derived daily CSVs contain a small number of rows whose reported OHLC fields violate the canonical high/low envelope. Rejecting the entire file discarded otherwise valid market-wide evidence, including the BENH row on 15 October 2026.

## Observed exceptions

- 14 October 2026: 354 source rows; 352 valid rows; 2 quarantined rows (KBLD86, NICD88).
- 15 October 2026: 349 source rows; 346 valid rows; 3 quarantined rows (CBLD88, CCBD88, KBLD86).

The anomalies are retained with their source line, symbol, raw row and reason. They are not silently corrected or admitted as valid OHLC.

## Parser behavior

- File/schema/session/duplicate-symbol failures remain fatal and return REJECTED.
- Row-level OHLC or numeric/activity anomalies are isolated in `quarantined_rows`.
- Valid rows remain available with status RESEARCH_ONLY_WITH_QUARANTINE.
- Symbol lookup returns QUARANTINED_ROW when that symbol exists only in the quarantine set; it does not mislabel it as absent.
- BENH remains absent from the 14 October archive file and present on 15 October with O/H/L/C 273/313.9/273/313.9, volume 90, turnover Rs26,634 and 9 transactions.
- All evidence remains research-only; production admission remains false.

## Evidence limitations

The archive is an unofficial third-party ShareSansar-derived source. Absence of BENH from the 14 October file is not proof of no exchange trade. The first-ever trade date remains unverified pending complete exchange-native first-session evidence.
