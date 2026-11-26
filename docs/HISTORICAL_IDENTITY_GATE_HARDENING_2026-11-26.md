# Historical instrument identity gate hardening — 2026-11-26

## Change
The dated instrument manifest validator now checks identity interval overlap across the complete validated lifecycle, not only instruments active on the requested as-of date.

It rejects overlapping effective-date intervals when either:
- the same security ID is assigned to multiple rows; or
- the same symbol is assigned to multiple rows.

The report includes the conflicting lifecycle row indexes and the duplicated identity dimension. Adjacent, non-overlapping intervals remain valid. The existing as-of active-universe duplicate checks remain in place.

## Regression coverage
Added tests for:
- a historical security-ID overlap outside the current as-of date;
- a symbol reused by a different security ID during an overlapping interval;
- valid adjacent intervals for the same identity.

The historical identity workflow now runs both the dedicated identity regression suite and the instrument manifest tests whenever the validator or its tests change.

## Safety boundary
This is an engineering validation improvement. It does not certify the 281-equity universe, establish official historical IDs, repair source data, authorize predecessor/successor price splicing, or promote any data to canonical/training use.

## Verification
GitHub Actions is expected to run from the workflow-path update. No test result is claimed until the run is observed and its conclusion is checked.
