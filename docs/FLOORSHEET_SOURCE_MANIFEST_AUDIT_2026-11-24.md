
# NEPSE floorsheet source manifest audit — 2026-11-24

## Scope and method

This audit inspected live Git trees through GitHub's repository API. It enumerates filenames, Git blob object IDs, and declared byte sizes; it does **not** download or validate CSV row contents. File counts and date spans are manifest evidence only, not proof of complete trading-session coverage or correctness.

## SocrateAI — \`socrateai-official/nepse-open-data\`

- Default branch recursive tree SHA: \`f602a5b61e68582d28834d16f71151a4bae98d5b\`
- Floorsheet subtree SHA: \`8dd17b8ddc956ca35c9da36e2529452bd0ea2aee\`
- Floorsheet CSV files enumerated: **658**
- First dated file: \`floorsheet/floorsheet_2024-01-01.csv\`
- Latest dated file in this tree: \`floorsheet/floorsheet_2026-11-19.csv\`
- Sum of Git-reported file sizes: **3,116,744,322 bytes** (~3.12 GB decimal)
- Example latest file blob: \`84c7afbda588fc5fcebc346a954172c43809c616\`, 2,383,640 bytes.
- Current tree folders include \`floorsheet/\`, \`meta/\`, \`ohlc_adjusted_stock/\`, \`ohlc_index/\`, and \`ohlc_unadjusted_stock/\`. The README's folder diagram is stale; use the actual tree as the current manifest.
- Repository LICENSE is MIT. Upstream data rights and source lineage still need separate verification before production use.

## SamirWagle — \`SamirWagle/Nepse-All-Scraper\`

- Floorsheet subtree SHA: \`340ed667d1dad1a877ddac6cb16e3654cb19daa8\`
- Floorsheet CSV files enumerated: **179**
- First dated file: \`data/floorsheet/floorsheet_2026-02-22.csv\`
- Latest dated file in this tree: \`data/floorsheet/floorsheet_2026-11-24.csv\`
- Sum of Git-reported file sizes: **734,702,749 bytes** (~735 MB decimal)
- Example latest file blob: \`c49e450858070205737ac09cd9fa4c2de22a5479\`, 2,886,747 bytes.
- Actual files are under \`data/floorsheet/\`, not the root-level path shown by the README example.
- Earlier source inspection found the scraper assigns today's date to the fetched page; this code is not evidence of date-parameterized historical backfill. The committed daily files still require row-level validation.
- The project describes itself as educational and cites ShareSansar/Merolagani. No separate data reuse grant was verified. Do not ingest or redistribute until terms/permission are clear.

## Cross-source date and blob comparison

Compared the dated CSV manifests in the two pinned floorsheet subtrees:

- Dates present in both manifests: **155**
- Dates present only in SocrateAI: **503**
- Dates present only in SamirWagle: **24**
- Exact Git blob matches on shared dates: **0 of 155**
- On 11 of the 155 shared dates, Samir's file is more than 10% smaller by byte size than SocrateAI's file.
- Largest size discrepancy in that direction: 2026-03-10 — SocrateAI 12,074,849 bytes; Samir 1,073,010 bytes (~8.9% of SocrateAI size). 2026-04-09 is also unusually small: 7,665,800? No — the manifest reports SocrateAI 6,363,390 bytes and Samir 766,580 bytes.

Interpretation:
- Different Git blob hashes prove the files are not byte-for-byte identical; they do **not** prove the records differ, because headers, quoting, line endings, ordering, or schema may differ.
- The large size reductions are high-priority completeness anomalies, not proof of missing transactions. They must be checked against row counts and daily contract sets after lawful file acquisition.
- The 24 Samir-only dates may reflect publisher coverage, file-date differences, or a source gap in SocrateAI. Do not classify them as verified exchange sessions from filenames alone.
- Neither source is promoted to canonical floorsheet storage by this manifest comparison.

## Coverage interpretation

- Date spans and file counts are filename-manifest evidence, not verified session counts.
- Calendar-day gaps are not classified as missing trading sessions: weekends, holidays, exchange closures, and publisher omissions must be distinguished using a verified session calendar.
- Samir's 179-file archive is a useful recent candidate, not a 2011+ historical floorsheet archive.
- SocrateAI's ~3.12 GB of CSV files could not be fetched through the current GitHub text connector. Failed fetch attempts are not successful downloads.
- No row-level quality or completeness claim is made.

## Acquisition gate and next tests

1. Confirm data-use rights and upstream lineage for each source.
2. Use the project acquisition utility to enumerate a pinned commit and, only after rights clearance, download to immutable raw storage with a positive total-byte ceiling.
3. Preserve URL, repository commit/tree SHA, path, Git blob SHA, byte size, retrieval timestamp, and local SHA-256.
4. For every CSV, validate header/schema, encoding, row count, date consistency, contract number as a string, duplicate/conflicting contract IDs, positive quantity/rate/amount, amount-vs-quantity×rate tolerance, buyer/seller broker fields, timestamp nullability, and daily control totals.
5. Reconcile per-date contract sets between independent sources. Do not compare only file size or aggregate turnover.
6. Reconcile file dates with other independent source manifests and official NEPSE notices. Never treat filename presence or a publisher's coverage percentage as proof of complete floorsheet capture.
7. Only after those gates pass may normalized rows enter canonical floorsheet tables; retain every source copy and correction as immutable evidence.

## Reproducibility

- SocrateAI recursive Git tree: \`https://api.github.com/repos/socrateai-official/nepse-open-data/git/trees/main?recursive=1\`
- SocrateAI floorsheet subtree: \`https://api.github.com/repos/socrateai-official/nepse-open-data/git/trees/8dd17b8ddc956ca35c9da36e2529452bd0ea2aee\`
- Samir floorsheet subtree: \`https://api.github.com/repos/SamirWagle/Nepse-All-Scraper/git/trees/340ed667d1dad1a877ddac6cb16e3654cb19daa8\`

Audit status: **manifest enumeration and cross-source filename/blob comparison complete; raw file acquisition and row-level validation not complete.**
