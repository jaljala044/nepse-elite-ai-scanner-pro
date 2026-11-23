# V3 data coverage audit

## Purpose
Measure actual daily OHLCV coverage before enabling the V3 scanner across the NEPSE universe. The audit does not infer trading sessions from calendar days and does not fabricate missing observations.

## Run
From `backend/`:

```bash
python audit_v3_coverage.py --input /path/to/combined_ohlcv.csv
```

For exact missing-symbol identification, supply the authoritative symbol master:

```bash
python audit_v3_coverage.py --input /path/to/combined_ohlcv.csv --universe /path/to/nepse_symbols.csv
```

For session-level completeness, supply a verified exchange-session calendar:

```bash
python audit_v3_coverage.py --input /path/to/combined_ohlcv.csv --universe /path/to/nepse_symbols.csv --sessions /path/to/nepse_sessions.csv --as-of 2026-11-20
```

Input OHLCV CSV columns: `symbol,date,open,high,low,close,volume`. Universe CSV requires `symbol`; session calendar CSV requires `date`.

## Interpretation
- `missing_symbols` is exact only when a master list is supplied.
- Without a session calendar, missing session counts remain null. Weekends and exchange holidays are not treated as missing trading sessions.
- `stale_calendar_days_as_of` is a calendar-age indicator, not a trading-session count.
- Duplicate symbol/date keys and invalid OHLCV rows are reported and excluded from valid unique coverage.
- A target count of 309 without a master list reports only a count gap; it cannot identify which names are missing.

The JSON report includes per-symbol first/latest dates, row counts, optional calendar gaps, stale age, and row-level errors. This is a coverage audit, not a certification of corporate-action adjustment, source accuracy, or tradability.
