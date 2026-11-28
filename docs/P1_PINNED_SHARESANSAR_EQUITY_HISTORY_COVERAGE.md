# P1 — pinned ShareSansar-derived equity history coverage inventory

This increment converts the completed 281-symbol archive retrieval into a
repeatable, machine-readable coverage job.

## Run

From `backend/`:

```bash
python -m pip install -r requirements.txt
python audit_sharesansar_equity_history.py \
  --crosswalk ../data/reference/nepse_equity_security_id_crosswalk_2026-11-26.csv \
  --output-dir ../data/reports
python -m unittest tests.test_sharesansar_equity_history -v
```

The job resolves the archive's mutable `master` branch once to a 40-character
commit SHA, requires a non-truncated Git tree, and checks every downloaded
symbol file against both the pinned Git blob SHA and byte count. It emits one
CSV row per crosswalk equity plus a JSON summary. Request failures and missing
paths remain explicit per-symbol statuses; they are never silently dropped.

## Coverage interpretation

Three- and five-year thresholds use calendar anniversaries between the first
and last parseable `d` values. They measure archive date span only. They do
not establish continuous daily coverage, exchange-session completeness,
valid OHLCV, effective-dated security identity, corporate-action treatment,
independent publisher lineage, or permitted reuse. All output is explicitly
ineligible for canonical data and model training.

The ShareSansar-derived archive remains a single lineage family. A second
mirror of the same upstream publisher is not independent confirmation. The
user's target remains at least three years per equity, preferring five years;
this job measures the gap and does not lower that target.

## Next acquisition dependency

For equities below three years, obtain provider-authorized exports/API access
from ShareHub, Chukul, or NEPSE Alpha. Do not guess private endpoints or use
credentials outside the provider's terms. Historical floorsheets require a
separate date-complete, timestamp-bearing acquisition path.
