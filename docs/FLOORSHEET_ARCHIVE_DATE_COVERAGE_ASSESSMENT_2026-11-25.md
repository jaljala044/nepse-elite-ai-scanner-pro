# Floorsheet archive date-file coverage assessment — 2026-11-25

## Scope and method

This report inventories the date-named floorsheet CSV files in two pinned public Git repository trees. The assessment window is:

- One-year candidate window: **2025-11-25 through 2026-11-25** (inclusive date filter; most recent file is 2026-11-24).
- Six-month candidate window: **2026-05-25 through 2026-11-25**.

This is a **date-file manifest count**, not a count of verified NEPSE trading sessions. The date-level official exchange calendar and exact target instrument universe are not yet available. A date-named file can be incomplete, misdated, or include instruments outside the requested working universe.

## Pinned repository snapshots

| Source | Pinned commit | All dated floorsheet files | First file date | Latest file date |
|---|---|---:|---|---|
| [SocrateAI NEPSE Open Data](https://github.com/socrateai-official/nepse-open-data) | \`cfa92493e93211c7019a5cd0b2cbe7d400d9c4e3\` | 661 | 2024-01-01 | 2026-11-24 |
| [SamirWagle NEPSE All Scraper](https://github.com/SamirWagle/Nepse-All-Scraper) | \`e6160adc6bdf3d19562167388e3d9d4f645c455a\` | 179 | 2026-02-22 | 2026-11-24 |

## Date-file counts

### One-year candidate window

| Window | SocrateAI files | SamirWagle files | Shared | SocrateAI only | SamirWagle only |
|---|---:|---:|---:|---:|---:|
| One year | **228** | **179** | **157** | 71 | 22 |

### Six-month candidate window

| Window | SocrateAI files | SamirWagle files | Shared | SocrateAI only | SamirWagle only |
|---|---:|---:|---:|---:|---:|
| Six months | **115** | **119** | **107** | 8 | 12 |

Neither archive's six-month date list is a superset of the other. The one-year file lists also have substantial date-set differences. The two repositories are therefore not interchangeable as a single "complete daily" source.

## Same-day contract-level evidence: 2026-11-24

The pinned files on this date were compared row by row:

| Measure | SamirWagle | SocrateAI |
|---|---:|---:|
| Data rows | 52,369 | 52,387 |
| Unique contract IDs | 52,369 | 52,387 |
| Malformed rows | 0 | 0 |
| Duplicate contract IDs | 0 | 0 |
| Quantity × rate formula mismatches | 0 | 0 |
| Quantity | 14,662,346 | 14,670,177 |
| Gross amount | NPR 5,551,668,556.66 | NPR 5,553,019,249.46 |

- All 52,369 contract IDs present in Samir exist in SocrateAI.
- All shared rows match exactly across trade date, symbol, buyer code, seller code, quantity, rate and amount.
- There are **18 SocrateAI-only contracts**, zero Samir-only contracts and zero shared-row field conflicts.
- These 18 additional contracts contribute 7,831 shares and NPR 1,350,692.80, exactly closing the difference to MeroLagani's indexed 2026-11-24 daily quantity and amount controls.
- The 18 additional contracts comprise 16 RSY2 rows, one NMLBBLP row and one ICFCD89 row.

This is high-quality same-day set and control-total consistency evidence. It does **not** prove independent source lineage: the reviewed Samir scraper is explicitly MeroLagani-derived, while SocrateAI's original capture route still requires independent provenance verification. The one-day result should not be generalized to other dates.

## Readiness decision for priority 89

- **One-year source-file potential exists** in the SocrateAI archive (228 date files in the date window), but one-year *session coverage* is not proven.
- The Samir archive has 179 files in the one-year window; its date set differs materially from SocrateAI.
- Both archives have over 100 date files in the six-month candidate window, but six-month session completeness is not proven.
- The source inventories do not by themselves show that every required security is covered each day.
- The 2026-11-24 sample confirms that a file can be mathematically clean and still miss 18 contracts; all per-day files require independent control totals or robust cross-source reconciliation.

**Result:** retain SocrateAI as the stronger one-day completeness candidate for 2026-11-24, but do not mark either archive as one-year or six-month complete. The coverage gate remains **review_required** until an official date-level NEPSE session calendar, official instrument registry and per-session/per-security coverage reconciliation are captured.

## Required next evidence

1. Primary NEPSE open/closed day calendar with source bytes, date-specific exceptions and a stable hash.
2. Dated 281-equity + 47-mutual-fund target register with security IDs, instrument types and effective lifecycle dates.
3. Daily control totals or a trusted row-complete reference for every date in the candidate window.
4. Per-date, per-security presence and expected coverage metrics, with separate treatment for suspensions, first listing, delisting, no-trade and missing-source days.
5. Exact licence/permission evidence before persistent canonical storage, training or redistribution.

No source file has been written into the project repository. The raw CSVs were fetched for this analysis and only metadata, derived checks and reports were committed. No canonical or model-training data was promoted.
