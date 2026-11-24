# NEPSE floorsheet source manifest audit — 2026-11-24

## Scope and method

This audit inspected the live Git trees through GitHub's repository API. It enumerates filenames, Git blob object IDs, and declared byte sizes; it does **not** download or validate the CSV row contents. File counts and date spans are manifest evidence only, not proof of complete trading-session coverage or correctness.

## SocrateAI — `socrateai-official/nepse-open-data`

- Default branch tree SHA: `f602a5b61e68582d28834d16f71151a4bae98d5b`
- Floorsheet CSV files enumerated: **658**
- First dated file: `floorsheet/floorsheet_2024-01-01.csv`
- Latest dated file in this tree: `floorsheet/floorsheet_2026-11-19.csv`
- Sum of Git-reported file sizes: **3,116,744,322 bytes** (~3.12 GB decimal)
- Example latest file blob: `84c7afbda588fc5fcebc346a954172c43809c616`, 2,383,640 bytes.
- The top-level README describes this as daily raw trade data. The README's other folder claims do not all match the current tree; the actual tree has `floorsheet/`, `meta/`, `ohlc_adjusted_stock/`, `ohlc_index/`, and `ohlc_unadjusted_stock/`. Treat the tree, not the stale README folder diagram, as the present manifest.
- LICENSE file is MIT. This is a repository-level license statement; upstream data rights and source lineage still need separate verification before production use.

## SamirWagle — `SamirWagle/Nepse-All-Scraper`

- Floorsheet directory tree SHA: `340ed667d1dad1a877ddac6cb16e3654cb19daa8`
- Floorsheet CSV files enumerated: **179**
- First dated file: `data/floorsheet/floorsheet_2026-02-22.csv`
- Latest dated file in this tree: `data/floorsheet/floorsheet_2026-11-24.csv`
- Sum of Git-reported file sizes: **734,702,749 bytes** (~735 MB decimal)
- Example latest file blob: `c49e450858070205737ac09cd9fa4c2de22a5479`, 2,886,747 bytes.
- Important correction to the repository README/layout: actual floorsheet files are under `data/floorsheet/`, not at `data/floorsheet_YYYY-MM-DD.csv` in the root of `data/`. The README's advertised root-level example URL is therefore not a valid current path.
- The source code inspected in the earlier discovery pass assigns today's date to the fetched page; it is not evidence of date-parameterized historical backfill. These dated repository files may be an accumulated daily archive, but each file still needs content-level checks.
- The project describes itself as educational and sources data from ShareSansar/Merolagani. No separate data reuse grant was verified. Do not ingest or redistribute until terms/permission are clear.

## Coverage interpretation

- The date spans above are filename minima/maxima, not verified session counts.
- Calendar-day gaps were deliberately **not** classified as missing trading sessions: weekends, holidays, exchange closures, and publisher omissions must be distinguished using a verified session calendar.
- Samir's 179-file archive is a useful newer candidate, but it is not a 2011+ historical floorsheet archive.
- SocrateAI has materially broader dated floorsheet manifests, but approximately 3.12 GB of CSVs are too large to fetch through the current GitHub text connector. The failed fetch attempts are not data-download success.
- Neither source is promoted to canonical floorsheet storage by this manifest audit.

## Acquisition gate and next tests

1. Confirm data-use rights and upstream lineage for each source.
2. Use a reproducible, resumable downloader in the project environment to acquire permitted files to immutable raw storage; preserve URL, repository commit/tree SHA, path, Git blob SHA, byte size, retrieval timestamp, and local SHA-256.
3. For every CSV, validate header/schema, encoding, row count, date consistency, contract number as a string, duplicate/conflicting contract IDs, positive quantity/rate/amount, amount-vs-quantity×rate tolerance, buyer/seller broker fields, timestamp nullability, and daily control totals.
4. Reconcile file dates with other independent source manifests and official NEPSE notices. Never treat filename presence or a publisher's coverage percentage as proof of complete floorsheet capture.
5. Only after those gates pass may normalized rows enter the canonical floorsheet tables; retain every source copy and correction as immutable evidence.

## Reproducibility

The manifest observations in this document came from:
- SocrateAI recursive Git tree: `https://api.github.com/repos/socrateai-official/nepse-open-data/git/trees/main?recursive=1`
- Samir floorsheet directory tree: `https://api.github.com/repos/SamirWagle/Nepse-All-Scraper/git/trees/340ed667d1dad1a877ddac6cb16e3654cb19daa8?recursive=1`

Audit status: **manifest enumeration complete; raw file acquisition and row-level validation not complete.**
