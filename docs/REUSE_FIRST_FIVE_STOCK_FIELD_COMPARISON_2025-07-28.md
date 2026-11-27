# Reuse-first field comparison — five securities, 2025-07-28

## Purpose

This is a field-level reconciliation of already-preserved project evidence. It is not a new data capture, not an official NEPSE certification, and not permission to overwrite the user's authoritative values. The machine-readable companion is `data/reports/reuse-first-five-stock-field-comparison-2025-07-28.csv`.

## Existing evidence used

- SocrateAI floorsheet archive, pinned revision `7648ec7ce9988e032975d6cf8bcc876ba7da7ae5`, raw blob `9c5533626b354d5fefca06d6762d51e0b9beaac6` (170,727 rows; 10,026,040 bytes). The previously completed replay isolated 1,931 contracts across the five target securities.
- Existing daily-board/chart archives and extracted five-stock rows; do not count two ShareSansar-derived archives as independent upstream lineages.
- Existing MeroLagani date-filtered Price History results for all five securities. Its field is explicitly labelled LTP; preserve that label.
- User-provided OHLC/chart and floorsheet quantity/turnover values remain authoritative for these five records.

## Reconciled tape arithmetic

| Symbol | Contracts | Quantity | Turnover (Rs) | Tape min–max (Rs) | Full-day VWAP (Rs) |
|---|---:|---:|---:|---:|---:|
| BGWT | 194 | 14,028 | 13,256,345.00 | 925.00–992.00 | 944.9918 |
| MEHL | 333 | 29,753 | 14,008,898.10 | 460.00–480.50 | 470.8399 |
| RAWA | 74 | 3,165 | 2,515,662.50 | 780.30–811.00 | 794.8381 |
| RHGCL | 1,030 | 296,715 | 103,872,614.40 | 341.40–362.00 | 350.0754 |
| ULHC | 300 | 32,288 | 16,273,342.10 | 495.00–515.00 | 504.0059 |

## Field-by-field findings

- **Quantity and turnover:** existing floorsheet replay totals reconcile to the archived daily-board totals for all five. This is a strong arithmetic consistency check, but it is not proof of exchange eligibility or independent upstream lineage.
- **High and Low:** the tape min/max agrees with the existing chart high/low for MEHL, RAWA, RHGCL and ULHC. BGWT's tape minimum is Rs 925, while its chart low is Rs 933.40; the difference is the preserved one-share contract `2025072801025823,BGWT,54,48,1.0,925.0,925.0,2025-07-28`. Do not delete, edit, or automatically exclude it. Its trade-type/segment flag remains unverified.
- **Open:** existing chart Open values are retained and have MeroLagani dated corroboration. The floorsheet archive contains no timestamps, so its row order cannot establish the first eligible regular-session trade. The opening value is not independently reconstructed from this tape.
- **LTP:** MeroLagani's dated LTP matches the existing Source A close candidate for all five. Preserve it as LTP; it is not proof of the exchange-designated official Close.
- **Official Close:** unresolved for all five. The competing ShareSansar-derived Close values align with full-day VWAP and remain a distinct measure. Do not map VWAP or LTP into official Close without the historical exchange method/field definition.
- **VWAP:** the existing floorsheet replay provides reproducible full-day VWAP arithmetic. Its eligibility scope (including treatment of odd-lot/de-prioritized trades) must be stated before using it as an official metric.

## Disposition

1. Keep the user's five records and supplied OHLC/chart/floorsheet values unchanged.
2. Treat quantity and turnover as tape-arithmetic reconciled; retain source/lineage caveats rather than describing them as exchange-certified.
3. Treat four securities' tape extrema as matching chart extrema arithmetically, pending eligibility confirmation. Keep BGWT Low quarantined against the one-share Rs 925 exception until its trade type is known.
4. Keep Open's chart value, MeroLagani LTP and official Close as separate concepts; no timestamps means Open/LTP cannot be reconstructed from tape order.
5. Keep official Close unresolved for all five; no record is promoted by this comparison alone.

## Minimal remaining gaps

- Recover timestamps or an authoritative sequence for the existing contracts if available in an already-owned export; otherwise record that Open/LTP cannot be reconstructed from this archive.
- Obtain the explicit trade-type/segment flag for the BGWT one-share contract from existing broker/exchange artifacts if available; otherwise retain only that field-level exception.
- Establish whether the existing daily-board/chart Close field represents NEPSE's designated official close under the method effective on 2025-07-28. Only if existing records cannot establish this should a targeted official record/method request be considered.

No full dataset recollection, new provider capture, API purchase, or change to canonical values was performed for this report.


## Superseding addendum — timestamped workbook replay and closure, 2026-11-27

This report's earlier statement that the floorsheet archive had no timestamps and that Close remained unresolved is superseded for the five target securities by the recovered existing `NEPSE_Floorsheet_Evidence.xlsx` workbook and replay documented in commit `e78c6c0938a4dd47f3db61e219101144974ed2a0`. The workbook contains timestamped ShareHub transactions and pagination logs. All 1,931 target contracts were replayed, and the final 15-minute weighted-average close matches ShareHub daily history for BGWT 957.17, MEHL 475.63, RAWA 796.90, RHGCL 357.05 and ULHC 510.75. These are accepted as project-level `verified_reconstructed_close`, not exchange-certified values. Final-window quantities/turnover: BGWT 4,030 / NPR 3,857,411.00; MEHL 1,470 / NPR 699,170.00; RAWA 230 / NPR 183,288.00; RHGCL 20,380 / NPR 7,276,603.00; ULHC 2,041 / NPR 1,042,446.10.

BGWT contract `2025072801025823` is identified at 13:21:49.720 NPT, buyer broker 54, seller broker 48, one share at NPR 925. Its identity/timestamp task is complete; explicit exchange trade-type classification remains pending. Published low NPR 933.40 is preserved separately from tape low NPR 925.00. This contract is outside the final 15-minute close window. P1-A, quantity/turnover reconciliation, and BGWT contract identification are closed; P1-B/C, the explicit BGWT trade-type flag, and broader P1 gates remain separate and open.
