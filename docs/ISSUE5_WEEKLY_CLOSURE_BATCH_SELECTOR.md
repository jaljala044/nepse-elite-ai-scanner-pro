# Issue #5 deterministic weekly-closure batch selector

This utility ranks date groups from the pinned repeated-adjacent candidate extract. It does not adjudicate individual OHLCV records.

## Invocation

```bash
python scripts/rank_issue5_weekly_closure_batches.py \
  --input /path/to/repeated_adjacent_ohlcv_candidates.csv \
  --exclude data/reference/issue5_registered_weekly_closure_dates.csv \
  --exclude-reviewed data/reports/issue5_next_five_weekly_closure_batches_4_2026-11-28.csv \
  --output /path/to/weekly_closure_batch.json \
  --limit 5
```

The checked-in exclusion register `data/reference/issue5_registered_weekly_closure_dates.csv` contains 20 previously reviewed dates from PRs #356, #367, #370 and #376. It includes both weekly-closure batches and the five separately tracked unknown-session dates from PR #370 so they are not repeatedly queued. The exclusion CSV must contain a `current_date` column listing every date already registered in prior batches.

Use the optional `--exclude-reviewed` input for additional review batches that must not be repeated but are **not** exchange-certified closure records. For batch 5, pass the batch-4 review CSV `data/reports/issue5_next_five_weekly_closure_batches_4_2026-11-28.csv`. Its dates remain T2/T3 schedule-priority records; excluding them from a work queue does not add them to the registered closure list or change their review-only status. The selector rejects overlap between the registered and prior-review files. The selector rejects malformed dates, unknown repositories, duplicate repository/symbol/date rows, and previous dates that are not earlier than current dates. A date is eligible only when both approved archives are represented and every pair row agrees on one previous date.

The schedule boundary is 2026-04-06: Friday/Saturday closures before the change, Saturday/Sunday closures from the change onward. Ranking is by candidate-pair incidence, then ascending date. The report preserves pair counts and unique-symbol counts separately.

## Safety

- This is a workload prioritizer, not a session-certification tool.
- T2/T3 schedule context never becomes T1 NEPSE attestation.
- Missing archive dates are not classified as no-trade, suspension, lifecycle or source omission.
- No source data, calendar, canonical store or training data is modified.
- The output always declares row adjudication incomplete and canonical/training promotion false.

## Tests

```bash
python -m unittest discover -s tests -p 'test_issue5_weekly_closure_selector.py' -v
```
