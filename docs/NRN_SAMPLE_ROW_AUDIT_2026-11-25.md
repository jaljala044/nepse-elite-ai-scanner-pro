# NRN sample row audit — 2026-11-25

## Scope and provenance

This is a narrow, reproducible sample inspection of the same relative path in two public repositories:

- `jaljala044/nepse-smc-data/03_stock_charts_ohlcv/NRN_OHLCV.csv`
- `jaljala044/nepse-history-starter/03_stock_charts_ohlcv/NRN_OHLCV.csv`

Both GitHub file fetches returned blob SHA-1 `a644cc5eaa176ad5bc3f08caf4db262e903940c6`. Identical blob IDs establish that the two repository paths contain byte-identical Git blobs for this file at the inspected default-branch state; they are not independent price-source corroboration.

## Observed file-level results

- Rows: 936
- Unique date keys: 936
- Duplicate date keys: 0
- First date: 2024-03-04
- Last date: 2026-11-20
- Adjacent pairs with exactly identical OHLCV values: 320

The adjacent identical-candle count is a data-quality flag, not a conclusion that those rows are wrong. It may represent carried-forward values, repeated vendor exports, or legitimate unchanged records. The file alone does not establish which explanation applies. No rows were deleted or altered.

Examples of adjacent identical pairs include 2024-03-07/08, 2024-03-08/09, 2024-03-10/11, and 2024-03-21/22. These examples warrant comparison against an authoritative session calendar and independent daily price/volume evidence. Do not infer sessions or non-sessions from weekdays in this audit.

## Consequence for the project

1. Matching ticker filenames across archives cannot be counted as independent corroboration.
2. The reported 525 matching ticker-file inventory still needs per-file hashes and row-level comparisons before its exact overlap/conflict counts are accepted.
3. The reconciliation engine now flags adjacent identical candles without removing them and quarantines rows with invalid OHLC bounds or non-integral/negative volume.
4. This sample does not validate the full NRN history, the 616-session calendar, or the broader stock universe.

## Reproduction

Fetch both files from their respective default branches and compare the returned Git blob IDs. For the repeated-candle count, compare each consecutive pair of rows' Open, High, Low, Close and Volume fields exactly, without date interpolation or normalization that changes source values.
