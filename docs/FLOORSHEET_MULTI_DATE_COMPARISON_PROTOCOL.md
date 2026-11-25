# Multi-date floorsheet comparison protocol

**Status:** engineering utility added; awaiting real multi-date execution against the pinned source archives.  
**Purpose:** compare the same NEPSE date across two independently stored floorsheet CSVs without selecting a canonical publisher.

## Runner

From the `backend/` directory:

```bash
python compare_floorsheet_manifest.py \
  --manifest path/to/overlap-manifest.json \
  --output data/reports/floorsheet-overlap-comparison.json
```

The manifest is a JSON object with a non-empty `pairs` array. Each pair contains:

- `trade_date`: a real calendar date in strict `YYYY-MM-DD` form;
- `left_path`, `left_format`: file path relative to the manifest directory and a supported source format (`samir` or `socrate`);
- `right_path`, `right_format`: the second source file and format;
- optional `left_sha256` and `right_sha256`: expected payload SHA-256 digests;
- optional `independent_control`: `trade_date`, `quantity`, and `gross_amount` from an independently captured daily control.

## Fail-closed checks

The runner rejects empty manifests, duplicate dates, invalid calendar dates, missing files, path traversal outside the manifest directory, unsupported source formats, malformed SHA-256 values, digest mismatches, and a control date that differs from the pair date.

For every date, it records both input hashes and invokes the contract comparator. It also verifies that both source files contain only the manifest's expected trade date. A date mismatch is retained as a failed date check and makes the overall report `review_required`; it is never silently normalized.

The report counts:
- exact contract-set and row-match dates;
- dates with missing/extra contracts or row differences;
- dates with shared-contract field conflicts;
- dates with independent-control failures;
- dates whose source rows do not match the manifest trade date.

## Interpretation

An exact two-source match is a consistency result, not proof of independent acquisition provenance, source rights, official exchange completeness, or full instrument-universe coverage. If one source contains additional contracts, those rows remain explicit; they are not automatically appended to the other source.

The runner always emits:
- `canonical_source_selected: false`
- `training_eligible: false`

No manifest result by itself authorizes canonical data promotion or model training. A date-level NEPSE session calendar, dated target instrument register, source lineage/rights, and independent daily controls remain separate acceptance gates.

## Current execution status

The new runner and regression tests are committed. The one-day 2026-11-24 comparison remains the only fully executed multi-source contract comparison documented so far. The multi-date utility must pass CI and then be run against a pinned overlap manifest before any historical coverage claim is upgraded.
