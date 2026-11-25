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


## Third overlap batch — next older 30 shared dates (priority 100, partial)

The third batch compared the 30 shared dates immediately preceding the previous 40-date window. Window: **2026-07-17 through 2026-09-01**.

- Samir physical rows: **1,649,223**.
- Samir unique contract IDs: **1,648,223**.
- SocrateAI rows and unique contract IDs: **1,650,258**.
- Shared contract IDs with exact row matches: **1,648,223**.
- SocrateAI-only contracts: **2,035**; Samir-only contracts: **0**; shared field conflicts: **0**.
- Raw source quantity surplus (SocrateAI minus Samir): **1,994,322 shares**.
- Raw source turnover surplus: **NPR 1,756,482,535.19**.
- Both sources: zero malformed rows, zero formula exceptions and all 30 source-date checks passed. Samir had one duplicate-ID quality exception on 2026-07-17.
- Broker-code coverage remained identical: 91 distinct codes across both sources, no source-only codes, and identical per-date code sets on all 30 dates.

### Newly isolated Samir duplicate-row anomaly — 2026-07-17

The duplicate-contract ledger captured **1,000 distinct contract IDs**, each appearing exactly twice in the Samir 2026-07-17 CSV (2,000 physical rows total; 1,000 extra rows). Every pair has identical transaction fields after excluding Samir's source sequence field `sn`; the two raw rows differ only in `sn`. The 1,000 extra copies contribute **182,280 shares** and **NPR 89,427,317.60** to Samir's raw file totals.

- 912 duplicate pairs are adjacent physical CSV lines; 88 are not adjacent.
- SocrateAI has no duplicate contract IDs in this 30-date batch.
- The 1,000 duplicate contract IDs are shared with SocrateAI; contract-level shared-row comparison still matches exactly after using unique contract IDs.
- This is strong evidence of a Samir source-file duplication anomaly, but it is not independently adjudicated. Both physical rows are retained in the ledger; no automatic deduplication or canonical data correction is applied.

If the 1,000 extra physical rows were later independently confirmed as duplicated captures, the Samir total would be lower by 182,280 shares and NPR 89,427,317.60 for this date. The source-to-source turnover difference would consequently increase by that amount. This adjustment is illustrative only and is not applied to the report's raw totals.

### Combined latest 70 shared dates

| Measure | Combined result |
|---|---:|
| Dates compared | 70 |
| Samir physical rows | 3,710,442 |
| Samir unique contracts | 3,709,442 |
| SocrateAI rows / unique contracts | 3,712,942 |
| Shared exact contract rows | 3,709,442 |
| SocrateAI-only contracts | 3,500 |
| Samir-only contracts | 0 |
| Shared-row field conflicts | 0 |
| Samir duplicate extra physical rows | 1,000 |
| Raw quantity surplus | 3,385,477 shares |
| Raw turnover surplus | NPR 1,851,925,427.67 |

The 70 dates are the latest 70 common date-named files out of 157 common files in the one-year candidate window. They are not 70 exchange-verified trading sessions. The 1,000 Samir duplicate physical rows are included in the raw source totals above; no corrected total is promoted. Independent daily control totals remain unavailable.

### Reproducibility

- [Third 30-date overlap and duplicate-ledger run 45598359940](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45598359940) — passed.
- [Backend suite run 45598359945](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45598359945) — **516 tests passed**.
- [Backend contract tests run 45598359986](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45598359986) — passed.
- [Integrated evidence audit run 45598360229](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45598360229) — passed.
- Artifact ID: `15014282629`
- Artifact ZIP SHA-256: `53d2850c1a35a8222fab0ed53efd16b7d4210a5b048fe770b477c0f483f17987`
- Duplicate ledger JSON SHA-256: `3e047277f5de91f00559959e4bd0f3f1ce018c25e4e94d1d6f996f9ad7dc60da`
- Duplicate ledger CSV SHA-256: `90d57079473d3fea35ff84d63865e41e855448ef2de9b347c5986aebce8bb06a`
- Report JSON SHA-256: `f621c5abf92be288c63a3389bd8c926a6b35cb6ed69da7df61cad2dc2d1bfc2a`
- Manifest SHA-256: `5c86a735d7c85a43fb9e0ddbed4062ae7471503655503eb59f166d929b8c397e`

The artifact contains derived reports and row-level exception ledgers, not the raw CSV payloads.


## Fourth overlap batch — 30 dates and first exact published daily control (priority 100, partial)

The fourth batch covers **2026-06-05 through 2026-07-16**, the next 30 common date-named files.

- Samir: 1,619,124 physical rows.
- SocrateAI: 1,668,638 physical rows.
- Shared contracts with exact row matches: 1,619,124.
- SocrateAI-only contracts: 49,514; Samir-only: 0; shared field conflicts: 0.
- Quantity surplus: 7,797,111 shares.
- Gross-turnover surplus: NPR 5,307,955,755.81.
- Both sources passed row syntax/math checks on all 30 dates; no duplicate contract IDs in this batch.
- Broker-code union: 91 codes in each archive. Per-date code sets matched on 29/30 dates; on 2026-06-24 code 73 appears only in SocrateAI.
- **48,917 of the 49,514 SocrateAI-only contracts are concentrated on 2026-06-24.** The other 29 dates account for 597 source-only contracts.

### 2026-06-24: first exact published daily control

The cross-publisher control is recorded in `data/independent_controls/floorsheet_daily_controls_2026-11-25.json` and detailed in `docs/INDEPENDENT_DAILY_CONTROL_CROSSCHECK_2026-06-24.md`.

The control is based on MeroLagani and ShareSansar reports of 10,777,582 shares and 72,917 transactions, plus The Rising Nepal page 2 reporting exact turnover of NPR 4,418,607,486.62. One conflicting secondary summary (HamroShare) is retained in the control file as unresolved evidence and is not used for acceptance.

Automated comparison against this control:

| Measure | Samir | SocrateAI | Published control |
|---|---:|---:|---:|
| Transaction rows | 24,000 | 72,917 | 72,917 |
| Quantity | 5,564,078 | 10,777,582 | 10,777,582 |
| Gross amount | NPR 1,874,967,415.91 | NPR 4,418,607,486.62 | NPR 4,418,607,486.62 |
| Control status | **failed** | **passed** | — |

The Samir file has exactly 24,000 rows, all 24,000 contract IDs are present in SocrateAI, and SocrateAI has 48,917 additional contracts across 237 symbols. This is strong evidence of an incomplete Samir capture on this date. The precise cause (pagination limit, source capture cutoff or another issue) is not yet established.

### Combined latest 100 shared dates

| Measure | Combined result |
|---|---:|
| Dates compared | 100 of 157 common date files |
| Samir physical rows | 5,329,566 |
| Samir unique contracts | 5,328,566 |
| SocrateAI rows / unique contracts | 5,381,580 |
| Shared exact contract rows | 5,328,566 |
| SocrateAI-only contracts | 53,014 |
| Samir-only contracts | 0 |
| Shared-row field conflicts | 0 |
| Samir duplicate extra physical rows | 1,000 |
| Raw quantity surplus | 11,182,588 shares |
| Raw gross-turnover surplus | NPR 7,159,881,183.48 |

The raw totals include the 1,000 duplicate Samir physical rows identified on 2026-07-17. Those rows remain preserved and unresolved; no corrected total is promoted. Only one of the 100 dates currently has a published daily control attached, and that control fails Samir but passes SocrateAI. The overall readiness status remains `review_required`.

### Reproducibility

- [Fourth 30-date audit with published control run 45599320707](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45599320707) — passed.
- [Backend suite run 45599320697](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45599320697) — **517 tests passed**.
- Artifact ID: `15014378224`
- ZIP SHA-256: `88bdf8da1f6830b51b945e10036ee73cb49c3f052ede78415008eef8871514b9`
- Report JSON SHA-256: `398c5172e870ead4de923541f8ce4235cffd80d3ac2ae84553bf3663014a1cfb`
- Manifest SHA-256: `513229359f641af126710dd7a48b3e36e5739d1db3f468d240306c5f32b3448a`

**57 of 157 common date-named files remain.** The 100-file overlap is not an authoritative session calendar and does not resolve source lineage/rights or the dated 281-equity + 47-mutual-fund register.
