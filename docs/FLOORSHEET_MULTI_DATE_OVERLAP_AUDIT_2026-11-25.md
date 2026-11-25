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


## Hash-linked source-only exception ledger

The same ten-date workflow now emits a separate JSON and CSV exception ledger. It contains **262 records**, all classified as `right_source_only` (SocrateAI-only). Each record retains trade date, contract ID, symbol, buyer/seller broker codes, quantity, rate, amount, both pinned source repositories/commits, both source filenames and SHA-256 digests.

- No shared-field conflicts were found, so there are no conflict-type entries in this ledger.
- All 262 records remain `unresolved_source_only_no_auto_selection`.
- The ledger is not a missing-trade verdict; it is a record of one source containing a contract absent from the other.
- Canonical selection and training eligibility remain false.

Latest workflow:
- [Multi-date comparison and exception-ledger run 45596489553](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596489553) — passed.
- [Backend suite run 45596489636](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596489636) — **509 tests passed**.
- [Backend contract tests run 45596451411](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596451411) — passed.
- [Integrated evidence audit run 45596451157](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596451157) — passed.

Ledger artifact:
- Artifact ID: `15012988544`
- ZIP SHA-256: `2433f2b88396f5461efefb60096a766d15c39a0943f28e6d8f42655476fc0056`
- Ledger JSON SHA-256: `691fb4f0301886bdba8163c5b8f0c0e7192fccdab1cc83a2498d7414bcea1f29`
- Ledger CSV SHA-256: `78562993608eda4a75cf49b61ccf915dd1e2c07e05da01880ea6bb3dfd221a1e`

The artifact contains the report, source manifest and derived exception ledger. It does not contain the raw CSV payloads.


## Cross-date broker-code coverage — priority 98

The ten-date audit now includes a separate raw broker-code activity report. Across the full sample:

- **91 distinct broker codes** appear in each publisher archive.
- The two sources have an identical 91-code union across the window.
- There are no source-only broker codes in either direction.
- Each of the 10 dates has identical buyer/seller broker-code presence across both sources.
- Six dates have 91 codes; four dates (2026-11-02 through 2026-11-05) have 90 codes.
- Code presence and buyer/seller observation counts are retained per date and per source in the CSV activity report.

This is code coverage only. It does not verify that a code maps to the same legal entity across all historical dates, and it does not identify beneficial owners. Effective-dated legal identity remains unresolved.

Broker evidence artifact:
- [Multi-date overlap audit run 45596771362](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596771362) — passed.
- Artifact ID: `15013881435`
- ZIP SHA-256: `dfd2d18a5266421e10394affe77619551da2afbaed79a20e385471c623214fc9`
- Broker coverage JSON SHA-256: `65b38c84aa29ce7cb7451c8ae8e327f422c970d3e75a6ef313a559721063689e`
- Broker activity CSV SHA-256: `64319f4ec844c3b25e741270d064907f43a379213cf79e11d88c7f01f32b4ab3`


## Second overlap batch — preceding 30 shared dates (priority 100, partial)

A second pinned batch selected the 30 common dates immediately preceding the latest ten-date pilot, without reusing those ten dates. Window: **2026-09-02 through 2026-10-27**.

- Samir: **1,489,600** contracts.
- SocrateAI: **1,490,803** contracts.
- Shared contract IDs and exact shared-row matches: **1,489,600**.
- SocrateAI-only contracts: **1,203**.
- Samir-only contracts: **0**.
- Shared-row conflicts: **0**.
- Quantity surplus: **1,203,481 shares**.
- Gross-turnover surplus: **NPR 75,484,775.62**.
- Both sources: zero malformed rows, duplicate contract IDs and quantity × rate / amount exceptions across these 30 dates; all 30 row-date checks passed.
- Broker-code union: 91 codes in each archive across the window, zero source-only codes, and identical per-date code sets on all 30 dates. Seven dates contained 90 codes; the other 23 contained 91.
- The derived exception ledger contains **1,203** unresolved SocrateAI-only contract records.

### Combined latest 40 shared dates

Combining this batch with the 10-date pilot above:

| Measure | Combined result |
|---|---:|
| Dates compared | 40 |
| Samir contracts | 2,061,219 |
| SocrateAI contracts | 2,062,684 |
| Shared exact contract rows | 2,061,219 |
| SocrateAI-only contracts | 1,465 |
| Samir-only contracts | 0 |
| Shared-row field conflicts | 0 |
| Quantity surplus | 1,391,155 shares |
| Gross-turnover surplus | NPR 95,442,892.48 |

These 40 dates are the latest 40 common date-named files, not 40 exchange-verified sessions and not all 157 common dates in the one-year candidate window. No independent daily control totals were supplied for this 30-date batch. The persistent source asymmetry is a high-priority reconciliation lead, not proof that all 1,465 rows are valid missing trades.

### Reproducibility

- [30-date overlap workflow run 45597195384](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45597195384) — passed.
- [Backend suite run 45597195251](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45597195251) — **513 tests passed**.
- Artifact ID: `15014345535`
- Artifact ZIP SHA-256: `70ca2ab0845f807403a046f38a61e06e69e9480b9e880137cccf13e1a477f561`
- Report JSON SHA-256: `161f35f40dfd23903a3f55505771f35e8fc74990868e3ba41001eda7c3184ec4`
- Manifest SHA-256: `0b44e5d35c69cfeecab556fb6101b94bcf5db475985805a1966f5349886bb54f`
- Exception ledger JSON SHA-256: `035a3ce3b6e27ee6409dbbb26c70787436cb1c69f24cf88eca2f4ad2c9e4496e`
- Broker coverage JSON SHA-256: `e277915e6bb111725acaa62fe31b007dfcad9a146ade3c7e736e7b327817b619`

The artifact contains only derived reports, manifests and exception/activity ledgers. Raw CSVs remained in the temporary runner workspace.
