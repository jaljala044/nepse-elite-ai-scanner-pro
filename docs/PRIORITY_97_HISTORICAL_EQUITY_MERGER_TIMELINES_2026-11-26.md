# Priority 97 — historical equity merger timeline evidence expansion (2026-11-26)

## Result

Added sourced joint-transaction start dates for six predecessor symbols to `data/reference/nepse_historical_identity_evidence_2026-11-26.json`.

| Predecessor symbol(s) | Successor | Joint-transaction start | Evidence |
|---|---|---:|---|
| BPW | Samudayik Laghubitta (SLBSL) | 2024-03-06 | ShareSansar merger/listing report |
| MMFDB, NLBBL | Nerude Mirmire Laghubitta (NMLBBL) | 2024-03-13 | ShareSansar merger/listing report |
| JALPA, KLBSL | Matribhumi Laghubitta (MATRI) | 2024-07-11 | ShareSansar merger-completion report; Merolagani announcement |
| MKLB | Samata Gharelu Laghubitta (SMATA) | 2024-07-08 | ShareSansar post-acquisition listing report |

## Evidence interpretation

- ShareSansar's 2024-05-17 report states that BPW and SLBSL commenced joint transactions on 24 Falgun 2080, and MMFDB/NLBBL commenced joint transactions on 30 Falgun 2080.
- Merolagani's MATRI announcement states that Kisan Laghubitta and Jalpa Laghubitta commence joint transactions under Matribhumi from 27 Ashad 2081; ShareSansar's 2024-07-11 notice independently reports merger completion effective that day.
- ShareSansar's 2024-08-02 report states that Samata Gharelu and Manakamana Smart commenced joint transactions on 24 Ashad 2081.

## Remaining limits

These dates identify the start of joint corporate operations. They do not, by themselves, establish:
- the last exchange trading date for each predecessor symbol;
- the first exchange trading date for the successor symbol;
- exact NEPSE security IDs and their validity intervals before/after the event;
- uninterrupted identity continuity or a permissible historical-price splice.

Accordingly, every affected JSON record continues to carry `stable_id: null` and `effective_date_verified: false`. No historical prices were spliced, no filenames or aliases were changed, and no raw OHLCV/floorsheet data was modified. This evidence does not authorize canonical identity promotion or model-training use.

## Source links

- https://www.sharesansar.com/newsdetail/after-successful-merger-shares-of-samudayik-laghubitta-and-nerude-mirmire-laghubitta-listed-in-nepse-2024-05-17
- https://www.sharesansar.com/newsdetail/joint-trading-of-kisan-laghubitta-and-jalpa-samudayik-laghubitta-shares-transactions-suspended-2024-07-11
- https://www.merolagani.com/AnnouncementDetail.aspx?id=54224
- https://www.sharesansar.com/newsdetail/after-successful-acquisition-share-of-samata-gharelu-laghubitta-listed-in-nepse-2024-08-02

## Additional merger timeline records — second batch

Four more predecessor symbols now have sourced joint-operation start dates in the machine-readable evidence:

| Predecessor symbol(s) | Successor | Joint-operation start | Evidence |
|---|---|---:|---|
| SABSL, SDLBSL | Sampada Laghubitta (SMPDA) | 2024-07-14 | ShareSansar completion/listing and merger notice |
| SAMAJ | Grameen Bikas Laghubitta (GBLBS) | 2025-10-19 | Merolagani merger announcement |
| SFCL | Pokhara Finance (PFL) | 2026-07-10 | ShareSansar unified-operation and NEPSE suspension reports |

The Sampada sources specify 30 Ashadh 2081 (2024-07-14); the notice published on 2024-07-08 is a pre-event announcement, not the joint-operation date itself. The Grameen Bikas source specifies 2 Kartik 2082 (2025-10-19). The Pokhara Finance sources specify 26 Ashadh 2083 (2026-07-10), with trading suspension effective from the integration date.

These remain corporate integration dates, not proof of exact last/first exchange trading dates or stable-ID intervals. All affected JSON rows continue to use `stable_id: null` and `effective_date_verified: false`. No price histories were spliced and no raw data changed.

Additional source URLs:
- https://www.sharesansar.com/index.php/newsdetail/after-successful-merger-between-sabsl-and-sdlbsl-shares-of-sampada-laghubitta-listed-in-nepse-2024-08-15
- https://www.sharesansar.com/newsdetail/after-the-successful-merger-of-sabaikolaghubitta-and-sadhana-laghubitta-to-commence-joint-transaction-from-ashadh-30-2024-07-08
- https://eng.merolagani.com/AnnouncementDetail.aspx?id=61940
- https://www.sharesansar.com/index.php/newsdetail/pokhara-finance-and-samriddhi-finance-to-begin-unified-operations-from-ashadh-26-after-merger-approval-2026-06-26
- https://www.sharesansar.com/newsdetail/nepse-suspends-trading-of-pokhara-finance-and-samriddhi-finance-shares-ahead-of-merger-2026-07-09


## Follow-up evidence expansion — explicit trading-suspension dates

Five predecessor records now have explicitly reported trading-suspension effective dates in the machine-readable identity evidence file:

| Predecessor symbol(s) | Suspension effective date | Evidence |
|---|---:|---|
| BPW | 2024-03-06 | ShareSansar notice: https://www.sharesansar.com/newsdetail/for-the-purpose-of-joint-integrated-transaction-share-trading-of-samudayik-laghubitta-and-bpw-laghubitta-to-be-halted-from-falgun-24-2024-03-06 |
| MMFDB, NLBBL | 2024-03-13 | ShareSansar notice: https://www.sharesansar.com/newsdetail/nerude-laghubitta-and-mirmire-laghubitta-trading-to-be-halted-from-falgun-30-2024-03-12 |
| SAMAJ | 2025-10-19 | NEPSE suspension effective Kartik 2, 2082: https://www.sharesansar.com/newsdetail/nepse-suspends-trading-of-gblbs-and-samaj-shares-ahead-of-merger-implementation-2025-10-17 |
| SFCL | 2026-07-10 | NEPSE suspension effective Ashar 26, 2083: https://www.sharesansar.com/index.php/newsdetail/nepse-suspends-trading-of-pokhara-finance-and-samriddhi-finance-shares-ahead-of-merger-2026-07-09 |

**Interpretation guardrail:** a suspension effective date is not necessarily the last date with an actual trade. These dates must not be used as last-trading dates, successor first-trading dates, or stable-ID boundaries without separate trade-history and listing evidence. JALPA/KLBSL and MKLB/SAMATA remain without separately verified suspension-effective dates. All affected `stable_id` and `effective_date_verified` values remain unchanged.


## Follow-up evidence expansion — predecessor last-recorded-trade dates

Three predecessor symbols now have explicit last-recorded-trade dates in secondary historical company records:

| Predecessor | Reported last recorded trade | Source | Evidence note |
|---|---:|---|---|
| JALPA | 2024-07-10 | https://laganilab.com/nepse-company/JALPA/ | Laganilab states last recorded trade 2024-07-10 |
| KLBSL | 2024-07-10 | https://www.merolagani.com/CompanyDetail.aspx?symbol=KLBSL | Merolagani reports last traded 2024/07/10 02:59:50; ShareSansar also reports the closing price on 2024-07-11 merger notice |
| MKLB | 2024-07-07 | https://laganilab.com/nepse-company/MKLB/ | Laganilab states last recorded trade 2024-07-07; Merolagani company detail reports 2024/07/07 02:59:35 |

For the JALPA/KLBSL group, Matribhumi (MATRI) shares were listed on 2024-08-12 and reported as available for trading from 2024-08-13. Sources: https://eng.merolagani.com/NewsDetail.aspx?newsID=104854 and https://nepsealpha.com/post/detail/5699/shares-of-matrubhumi-laguvitta-listed-on-nepse-trading-from-today.

**Boundary caution:** these are secondary-source historical last-trade reports. The MATRI listing/first-trading report establishes the successor's market commencement at the reported date, but does not by itself establish an uninterrupted security-ID mapping or authorize price-history splicing. MKLB's last-trade evidence is consistent with its acquisition/suspension sequence, while SMATA is the continuing listed successor ticker. All stable_id values remain null and effective_date_verified remains false pending dated security-ID evidence and a full raw price-history cross-check. No OHLCV or floorsheet data was modified.


## OHLCV boundary validation — JALPA/KLBSL and MKLB (2026-11-26)

### Method

Read-only inspection of the symbol CSVs under `03_stock_charts_ohlcv/` in both `jaljala044/nepse-smc-data` and `jaljala044/nepse-history-starter`. The two repositories' Git trees show identical blob SHAs for every predecessor/successor file in the merger set inspected. For the four files below, the CSV contents were parsed and first/last rows checked. This validates repository-file boundaries, not exchange-original data lineage or legal security identity.

### Observed file boundaries

| Symbol | File boundary | Boundary row | SHA-1 Git blob |
|---|---|---|---|
| JALPA | Last row 2024-07-10 | O 1465.00 / H 1480.00 / L 1430.00 / C 1442.10 / Vol 6,339 | `126b765ab3cab5bc8f6718a602fe0551ac5a1680` |
| KLBSL | Last row 2024-07-10 | O 1051.50 / H 1113.10 / L 1051.50 / C 1070.00 / Vol 3,998 | `d993854149e820b123cf8f78e11c8b8001a9c432` |
| MATRI | First row 2024-08-13 | O 1303.90 / H 1406.20 / L 1303.90 / C 1406.20 / Vol 1,391 | `fc6c9f1acb505a866bd64c76ccf83fb11c0201d7` |
| MKLB | Last row 2024-07-07 | O 1205.00 / H 1205.00 / L 1142.00 / C 1169.00 / Vol 15,057 | `7b2289dd319c3abad706c12d937609d1f08f441f` |
| SMATA | First row 2024-03-04 | O 600.00 / H 600.70 / L 600.00 / C 600.70 / Vol 121 | `09c11f751108336a9843b586b1c3621a53d02dac` |

The JALPA and KLBSL files end on 10 July 2024; MATRI begins on 13 August 2024. The gap is visible in the repository files and must not be filled by carrying forward, interpolating, or concatenating rows. The MATRI first row is consistent with the separately reported first trading date, but exchange-primary identity/ID linkage remains unverified.

MKLB ends on 7 July 2024. SMATA is not a newly commencing successor series in this archive: its existing OHLCV file begins on 4 March 2024, well before the MKLB acquisition integration date. This is an acquisition into an already-traded successor symbol, so the predecessor and successor histories overlap in calendar time. Do not append MKLB rows to SMATA as if they were a single uninterrupted instrument. Any event-study continuity treatment requires explicit corporate-action and security-ID methodology.

### Cross-repository result

For all 17 merger-set CSV paths found in both repositories (BPW, GBLBS, JALPA, KLBSL, MATRI, MKLB, MMFDB, NLBBL, NMLBBL, PFL, SABSL, SAMAJ, SDLBSL, SFCL, SLBSL, SMATA, SMPDA), the Git blob SHAs and file sizes are identical between the two repositories. Therefore, this is exact replication across the two archives, not independent-source corroboration.

### Disposition

- JALPA/KLBSL predecessor end rows and MATRI first row: repository-boundary check passed; external lineage and stable-ID interval not certified.
- MKLB predecessor end row and SMATA pre-existing history: overlap confirmed; direct history splice prohibited.
- No raw OHLCV files were changed.
- `stable_id` remains null and `effective_date_verified` remains false for affected records.
- No canonical universe promotion, model-training promotion, or synthetic boundary row was created.


## Additional predecessor OHLCV boundary observations

The read-only review was extended to BPW, MMFDB, NLBBL, SAMAJ, SFCL, SABSL and SDLBSL. Exact file blobs are shared by both repositories, as described above.

| Predecessor | Last file row / distinct OHLCV observation | Interpretation |
|---|---|---|
| BPW | 2024-03-06, volume 1,900 | The file contains a nonzero-volume row on the reported suspension-effective date. Exact notice timing must be checked before calling it the final trade. |
| MMFDB | 2024-03-12, volume 25,868 | File ends one day before reported 2024-03-13 suspension. |
| NLBBL | 2024-03-12, volume 20,276 | File ends one day before reported 2024-03-13 suspension. |
| SAMAJ | Last distinct row 2025-10-16, volume 2,893; file continues through 2025-10-18 | 17 and 18 October repeat the 16 October OHLCV exactly; these are forward-filled rows, not evidence of additional trading sessions. |
| SFCL | 2026-07-09, volume 5,290 | File ends one day before reported 2026-07-10 suspension/integration. |
| SABSL | Last distinct row 2024-07-11, volume 10,540; file continues through 2024-07-13 | 12 and 13 July repeat the 11 July OHLCV exactly. |
| SDLBSL | Last distinct row 2024-07-11, volume 15,863; file continues through 2024-07-13 | 12 and 13 July repeat the 11 July OHLCV exactly. |

Successor files show that SLBSL, GBLBS and PFL already had OHLCV histories before the respective integration events; they are not cleanly newly-started successor series in these archives. NMLBBL's first file row is 2024-05-19; SMPDA's first file row is 2024-08-18. The file start is not automatically the legal first-trading date. All these boundary checks remain repository observations, not exchange-primary certification.

**Data-quality guardrail:** a repeated OHLCV row with nonzero volume can be a carried-forward value in these files. The terminal row date alone is therefore not a safe proxy for last trade. Distinct row/signature analysis and source trading calendar evidence are required before promoting last-trade dates.


## Security-ID reconciliation — dated successor snapshot (2026-11-26)

The dated 2026-11-25 security-ID snapshot (`data/reference/nepse_security_id_snapshot_2026-11-25.csv`, Git blob `ed548857eb550fbb237910eb903fc202751c63a1`) supplies current successor mappings:

| Successor | Security ID | Snapshot date |
|---|---:|---:|
| SLBSL | 2804 | 2026-11-25 |
| NMLBBL | 396 | 2026-11-25 |
| MATRI | 694 | 2026-11-25 |
| SMATA | 2761 | 2026-11-25 |
| SMPDA | 2896 | 2026-11-25 |
| GBLBS | 583 | 2026-11-25 |
| PFL | 236 | 2026-11-25 |

These are **current snapshot IDs only**. They are not backdated into predecessor periods and do not establish whether an ID was retained, replaced, or reassigned across a merger. The unmatched-symbol review still lists the predecessor symbols BPW, JALPA, KLBSL, MKLB, MMFDB, NLBBL, SABSL, SAMAJ, SDLBSL and SFCL as unresolved historical identities. No predecessor ID is inferred from ticker similarity, successor company name, or current ID.

Disposition: successor snapshot IDs are attached as dated observations in the JSON evidence file; predecessor historical IDs, ID validity intervals, and legal continuity remain unresolved. No `stable_id` values are populated and no price history is linked or spliced.


## Follow-up evidence expansion — BPW / MMFDB / NLBBL last-recorded-trade dates

Three more predecessor records now have reported last-recorded-trade dates in secondary historical company records:

| Predecessor | Reported last recorded trade | Evidence |
|---|---:|---|
| BPW | 2024-03-06 | Laganilab historical company page explicitly reports the last recorded trade on 6 March 2024; its archive OHLCV file also has a nonzero-volume row on that date. |
| MMFDB | 2024-03-12 | Merolagani reports last traded at 14:58:52 on 12 March; ShareSansar's historical company page independently shows the 12 March close and volume. |
| NLBBL | 2024-03-12 | Merolagani reports last traded at 14:59:57 on 12 March; ShareSansar's historical company page independently shows the 12 March close and volume. |

The MMFDB/NLBBL dates are one calendar day before the reported 13 March 2024 suspension/joint-operation date. BPW's reported final trade and archive OHLCV row coincide with the reported suspension-effective date of 6 March 2024; this confirms why suspension date must not be substituted for the last-trade date without intraday chronology. These are secondary historical-source observations, not NEPSE-primary certified trade logs.

Sources:
- https://laganilab.com/nepse-company/BPW/
- https://merolagani.com/CompanyDetail.aspx?symbol=MMFDB
- https://merolagani.com/CompanyDetail.aspx?symbol=NLBBL
- https://www.sharesansar.com/index.php/company/mmfdb
- https://www.sharesansar.com/company/nlbbl

No historical security IDs or validity intervals were inferred. `stable_id` remains null and `effective_date_verified` remains false; no price histories were spliced and no raw OHLCV/floorsheet files were modified.
