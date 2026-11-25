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


## Follow-up acquisition — Yonepse daily JSON (2026-11-24)

A second public acquisition route was tested after the Hugging Face CSV and Google Drive routes were inaccessible.

- Repository: `Shubhamnpk/yonepse`
- Exact file retrieved through GitHub Contents API: `data/floor_sheet/daily/2026-11-24.json`
- Public raw-file convention is documented in the repository README; the exact JSON content was retrieved and parsed in this session.
- Payload date: `2026-11-24`
- Fields: `contractId`, `stockId`, `buyer`, `seller`, `qty`, `rate`, `amount`, `time`
- Rows: 52,387; unique contract IDs: 52,387.
- Recomputed quantity: 14,670,177 shares (matches the JSON summary).
- Recomputed amount: NPR 5,553,019,249.459984 (matches the JSON summary within floating-point representation).
- The JSON summary reports 52,387 trades.

### Exact cross-source comparison

Pinned comparison inputs:
- Yonepse: `https://api.github.com/repos/Shubhamnpk/yonepse/contents/data/floor_sheet/daily/2026-11-24.json`
- SocrateAI: `socrateai-official/nepse-open-data`, commit `cfa92493e93211c7019a5cd0b2cbe7d400d9c4e3`, `floorsheet/floorsheet_2026-11-24.csv`
- Samir/MeroLagani-derived: `SamirWagle/Nepse-All-Scraper`, commit `e6160adc6bdf3d19562167388e3d9d4f645c455a`, `data/floorsheet/floorsheet_2026-11-24.csv`

Results:
- Yonepse vs SocrateAI: 52,387/52,387 contract IDs matched; zero unmatched IDs in either direction; zero conflicts across buyer, seller, quantity, rate and amount.
- Yonepse vs Samir: all 52,369 Samir contract IDs are present in Yonepse; 18 Yonepse contracts are absent from Samir; zero conflicts across buyer, seller, quantity, rate and amount on shared contracts.
- SocrateAI totals: 52,387 rows, 14,670,177 shares, NPR 5,553,019,249.45998.
- Samir totals: 52,369 rows, 14,662,346 shares, NPR 5,551,668,556.660005.

This reproduces the earlier finding that the 18 extra contracts explain the entire difference between Samir and the larger 2026-11-24 dataset. The exact Yonepse–SocrateAI row match is **not independent corroboration**. Shared upstream capture, copying or derivation remains possible and has not been resolved. Yonepse is registered as a matching mirror/corroborating representation for this one date, not as an independent source.

### Integrity and remaining limits

- The payload was retrieved and parsed from the GitHub Contents API in this work session; it was not committed as a raw data artifact to the project.
- A local byte-for-byte payload file and independently computed SHA-256 were not produced in this session. Do not treat the API response as a durable pinned acquisition artifact.
- Yonepse uses `stockId`, while the compared CSVs use symbols. This comparison did not independently validate stock-ID-to-symbol mapping.
- The comparison is limited to 2026-11-24. It does not establish historical date coverage, completeness across all sessions, effective-dated broker identity, upstream source independence, or commercial/training rights.
- No canonical source selection or training-data promotion is authorized.

### Updated Priority 92 decision

**Partially complete for one-day payload retrieval and reconciliation; still open for durable byte pinning and source independence.** The Google Drive folder remains inaccessible because its connector is disabled by the workspace administrator. The Hugging Face candidate remains metadata-only. The project now has an additional exact one-day representation to use in the source-lineage investigation, but not a verified independent third source.


### Immutable Git object pin added

The Yonepse file was resolved to its file-specific commit and Git tree entry, then re-fetched at that exact commit:
- File commit: `1bfa798e84c7170f826e473e7e1ec3957c81966c` (2026-11-24T11:18:50Z; unsigned GitHub Actions commit)
- Tree: `33e7fc54f0b225e92d148f0ef362fbb67045abcd`
- Git blob SHA-1: `2a758194c470048e3b22aefc8954365397d9c48d`
- Exact file size reported by Git tree: 3,037,252 bytes
- Pinned-content re-fetch: 52,387 rows, 52,387 unique contract IDs, quantity 14,670,177, amount NPR 5,553,019,249.459984.

This provides a durable Git commit/tree/blob identity for the retrieved object, but **not an independently computed SHA-256**. The blob is pinned and reproducible from GitHub; local raw-byte retention and SHA-256 remain outstanding.


### Publisher-declared acquisition lineage review

Yonepse's pinned repository README and `pages/sources.html` identify the NEPSE Official API as the primary source for live prices, index snapshots, disclosures and floor sheets. Its `official_scraper.py` contains a transformation function that converts API-style fields (`contractId`, `stockId`, `buyerMemberId`, `sellerMemberId`, `contractQuantity`, `contractRate`, `contractAmount`, `tradeTime`) into the observed compact floor-sheet array. The same repository credits SocrateAI separately for longer historical index series.

This is useful publisher-side lineage evidence and makes Yonepse a plausible independently captured NEPSE-API representation. However, the 2026-11-24 raw API response, request/response logs, and capture-time hashes are not preserved in the reviewed artifact. Therefore the upstream path is still a publisher claim, not independently verified capture provenance. The exact match to SocrateAI remains consistent with both reflecting the same exchange records; it does not by itself prove copying or independent capture.
