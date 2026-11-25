# Ten-date floorsheet overlap audit — 2026-11-25

## Executive result

A bounded, reproducible comparison was executed across the **10 most recent dates present in both pinned public floorsheet archives** within the one-year candidate window (2025-11-26 through 2026-11-25).

- Samir / MeroLagani-derived source: **571,619** contracts across 10 files.
- SocrateAI source: **571,881** contracts across 10 files.
- Shared contract IDs: **571,619**; every shared contract matched exactly across date, symbol, buyer, seller, quantity, rate and amount.
- SocrateAI-only contracts: **262**.
- Samir-only contracts: **0**.
- Shared-contract field conflicts: **0**.
- Both sources: zero malformed rows, duplicate contract IDs and quantity × rate / amount formula exceptions in the 10 sampled files.
- Source row dates matched each manifest date on all 10 dates.
- SocrateAI totals exceed Samir by **187,674 shares** and **NPR 19,958,116.86** across these 10 dates.

**Decision:** strong repeated row-level consistency on the shared set, with a consistent SocrateAI-only surplus. This does not prove which publisher is complete, does not establish independent acquisition lineage, and does not provide independent daily controls for these 10 dates. Keep the result review-only.

## Per-date results

| Date | Samir rows | SocrateAI rows | Shared exact rows | SocrateAI-only | Quantity surplus | Turnover surplus (NPR) |
|---|---:|---:|---:|---:|---:|---:|
| 2026-10-28 | 63,732 | 63,744 | 63,732 | 12 | 5,080 | 189,585.50 |
| 2026-10-29 | 69,587 | 69,619 | 69,587 | 32 | 63,858 | 12,143,314.75 |
| 2026-10-30 | 74,032 | 74,054 | 74,032 | 22 | 9,400 | 198,570.00 |
| 2026-11-02 | 70,188 | 70,228 | 70,188 | 40 | 6,325 | 308,070.10 |
| 2026-11-03 | 57,426 | 57,449 | 57,426 | 23 | 15,515 | 294,867.50 |
| 2026-11-04 | 59,146 | 59,185 | 59,146 | 39 | 34,250 | 592,094.50 |
| 2026-11-05 | 44,394 | 44,412 | 44,394 | 18 | 3,015 | 44,449.50 |
| 2026-11-19 | 40,818 | 40,837 | 40,818 | 19 | 2,450 | 22,432.00 |
| 2026-11-20 | 39,927 | 39,966 | 39,927 | 39 | 39,950 | 4,814,040.21 |
| 2026-11-24 | 52,369 | 52,387 | 52,369 | 18 | 7,831 | 1,350,692.80 |
| **Total** | **571,619** | **571,881** | **571,619** | **262** | **187,674** | **19,958,116.86** |

Every shared contract row matched exactly; the difference is entirely represented by the SocrateAI-only rows. No shared-row field conflict was found.

## Reproducibility and pinned provenance

- Samir repository commit: `e6160adc6bdf3d19562167388e3d9d4f645c455a`
- SocrateAI repository commit: `cfa92493e93211c7019a5cd0b2cbe7d400d9c4e3`
- Git tree entry blob SHA-1 was recomputed from each downloaded payload and verified before parsing.
- Each downloaded payload also received a SHA-256 in the manifest.
- The acquisition workflow selected the latest 10 common date-named files from the explicit one-year window; this is a bounded sample, not a random or statistically representative sample.

GitHub Actions:
- [Multi-date overlap audit run 45596074299](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596074299) — passed.
- [Backend test run 45596074194](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596074194) — **506 tests passed**.

Artifact:
- Artifact ID: `15013057991`
- ZIP SHA-256: `c0c0153df5534876fa3346ddbf3e66ec94f42ad36e3a3181bfde0a449d301c6a`
- Report SHA-256: `5c743bec5e0535817304e142e88fa8942d4f2b411cea42e17da3ed10eebab15e`
- Manifest SHA-256: `14fe0a9cf4c0298a6b1c7b93f53bef1f7f5f27731357571c23e0f3d76563df81`

The artifact contains the comparison report and source manifest only. Raw CSV files were kept in the temporary GitHub Actions runner workspace and were not uploaded to the project repository or artifact.

## Interpretation and limitations

1. **Shared-row consistency is high:** 571,619 of 571,619 shared contract IDs match exactly across all seven compared fields.
2. **Source-set asymmetry repeats:** SocrateAI contains additional records on all 10 sampled dates, while Samir has no source-only contract on these dates.
3. **No independent daily controls were supplied for these 10 dates.** The quantity and turnover surplus is a source-to-source difference, not a proven missing-trade count.
4. **Provenance independence remains unresolved.** Samir's scraper is traceable to MeroLagani. SocrateAI's original upstream collection route is not independently proven.
5. **Instrument scope remains unresolved.** The CSV symbol set is not an authoritative 281-equity + 47-mutual-fund membership list. Do not silently drop or relabel securities.
6. **No canonical selection or model-training promotion.** The report's `canonical_source_selected` and `training_eligible` fields remain false.

## Next evidence needed

- Obtain independent daily MeroLagani/NEPSE control totals for the sampled dates, including contract counts where available.
- Inspect the 262 SocrateAI-only records by date and symbol, and reconcile them against the original page/API evidence rather than treating them as automatically valid or missing from Samir.
- Expand the same audit from 10 dates to all 157 shared dates in the one-year candidate window, preferably in bounded batches.
- Obtain the primary NEPSE session calendar and dated security register before declaring session or per-security coverage complete.
