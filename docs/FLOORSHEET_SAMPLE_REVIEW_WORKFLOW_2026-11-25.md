# Floorsheet sample review workflow

**Date:** 2026-11-25  
**Status:** Engineering path available; no user archive/sample was accessed in this run.

## 1. Inventory the outer ZIP

Use the non-extracting preflight documented in `FLOORSHEET_ARCHIVE_INVENTORY_GUIDE_2026-11-25.md`. Save the report and retain the exact outer archive SHA-256. A `safe_to_extract` result is only a structural safety result, not data approval.

Date-like member names are reported as `unverified_filename_candidate_only`. They are not treated as exchange sessions.

## 2. Select a small representative CSV sample

Review the inventory and select exact member paths. Prefer one or a few representative dates and a small size cap. Do not extract the whole archive just to discover its schema.

The extraction helper is `backend/extract_reviewed_floorsheet_members.py`:

```python
from extract_reviewed_floorsheet_members import extract_reviewed_csv_members

result = extract_reviewed_csv_members(
    "path/to/floorsheet.zip",
    "data/raw/floorsheet_sample",
    member_names=["floorsheet/2026-11-24.csv"],
    expected_archive_sha256="<reviewed outer ZIP SHA-256>",
    max_total_extracted_bytes=50 * 1024 * 1024,
    max_member_bytes=50 * 1024 * 1024,
)
```

The function refuses unsafe inventories, mismatched archive hashes, non-CSV members, unlisted members, duplicate allowlist entries, size-limit breaches and overwrites. It records a SHA-256 for each extracted member after full read/CRC verification.

## 3. Review the CSV header mapping

Use `app.floorsheet_csv_adapter.CsvFloorsheetMapping` with the exact source header strings. The normalized fields are:

- `trade_date`
- `contract_id`
- `symbol`
- `buyer_broker_code`
- `seller_broker_code`
- `quantity`
- `rate`
- `amount`

Do not guess mappings from column position or similar names. The adapter preserves the input payload SHA-256, physical row number and raw rejected rows.

## 4. Build the sample acceptance report

Pass the adapter result and `reconcile_floorsheet_rows(parsed["rows"])` to `app.floorsheet_sample_audit.build_floorsheet_sample_acceptance_report`.

Set `mapping_reviewed=True` only after a person has checked the source header mapping. Supply `verified_session_dates` only when date-level primary exchange evidence exists. Any other sample dates remain visible as unverified.

The report summarizes date range, date coverage status, symbols, buyer/seller broker codes, duplicates, amount reconciliation exceptions, rejected-row ratio, total quantity and amount. A clean sample can only reach `passed_for_rights_review`; it is not canonical or training data.

## 5. Governance gate

The sample report intentionally leaves `source_rights_status=not_assessed`, `promotion_allowed=false` and `training_eligible=false`. A clean parse does not establish that the publisher has rights to the underlying NEPSE data or that the archive is complete and independent of other mirrors.
