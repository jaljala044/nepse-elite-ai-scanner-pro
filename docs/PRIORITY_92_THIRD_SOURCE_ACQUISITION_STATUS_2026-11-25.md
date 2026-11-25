# Priority 92 — third-source Parquet acquisition and Drive intake status (2026-11-25)

## Outcome

**Not complete: raw Parquet bytes were not acquired.** The user supplied a Google Drive folder URL for a >1 GB archive, but the Google Drive connector is marked `DISABLED_BY_ADMIN` with installation policy `NOT_AVAILABLE` in this environment. There is no enabled Drive action capable of listing or downloading that folder. The folder was not opened, downloaded, inventoried or parsed.

A public Hugging Face route was retried. The dataset landing page and viewer are accessible, but the exact Parquet payload route is not accessible through the available browser retrieval path (the file/tree open returned an internal access error). No payload bytes or independent SHA-256 were obtained. Do not claim Priority 92 passed.

## Public metadata that can be used for later validation

The Hugging Face dataset page describes:
- `floorsheet/` as executed-contract records claimed to come from NEPSE, beginning 2026-08-19.
- a stated capture gap from 2026-08-26 through 2026-11-18.
- a Dataset Viewer preview with 1.22M rows across the overall dataset and displayed fields including `business_date`, `symbol`, `bar_ts`, OHLC, volume, turnover, trades and VWAP. This preview is not proof of the raw floorsheet table schema; it may represent a derived table.
- the dataset card's licence metadata is `other`, and its use note says research/educational use and that commercial redistribution may require a NEPSE licence.

References:
- https://huggingface.co/datasets/AnkitSanjyal/nepse-market-data
- https://huggingface.co/datasets/AnkitSanjyal/nepse-market-data/viewer
- https://ankitsanjyal.github.io/projects/nepse-pipeline.html

## Required next input / action

1. Enable the Google Drive connector at the workspace/admin level, then reconnect it; or
2. Upload one representative daily floorsheet CSV/Parquet file directly in chat (prefer a single session and a modest file size), not the full >1 GB ZIP.
3. If uploading from the archive, include the original filename and the date it represents. Do not edit/re-save the file before upload.
4. After bytes are available, compute SHA-256 locally, inspect physical schema/headers, parse into canonical contract fields, and reconcile row counts, contract IDs, quantity and turnover against overlapping sources.
5. Keep source rights and upstream lineage as separate acceptance gates. Public availability or code MIT licence is not evidence that raw exchange data is licensed for commercial redistribution or model training.

## Priority status

- Priority 91: third-source lead registered; candidate metadata pinned; payload verification pending.
- Priority 92: **blocked — no raw payload bytes acquired**.
- Priority 93 onward: multi-source row-level comparison must wait for an acquired sample.
- No data was promoted to canonical or training datasets.
- No claims are made about the contents of the user's Google Drive folder.
