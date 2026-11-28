# NRN retrospective reference comparison

Actual archived prices, not certified fills or approved backtest. Calculated in JavaScript using the same fixed rules as part5_reference_comparison.py; Python parity/CI pending. Archive origin/adjustment and historical availability unverified. Calendar is project accepted, not exchange certified. Single symbol chosen because existing NRN audit identifies pinned blob, not a representative universe. Duplicate accepted-session signatures quarantined; no forward fill. Entry next session open, exit fifth session close; nonoverlap per rule, fixed one percentage-point scenario cost. No settlement/price-limit/market-impact simulation or independent holdout. 20-session momentum and breakout are simple proxies, not authentic IDPAT/SMC. No claims of strategy edge.

```json
{
  "classification": "retrospective_price_reference_only",
  "symbol": "NRN",
  "archive_blob": "a644cc5eaa176ad5bc3f08caf4db262e903940c6",
  "calendar_blob": "c5fe82bea1796fd14a004878c1c7178a75c0bf31",
  "raw_rows": 936,
  "accepted_calendar_dates": 3630,
  "repeated_session_candidates": 0,
  "period": [
    "2025-01-01",
    "2025-12-31"
  ],
  "holding_sessions": 5,
  "assumed_cost_percentage_points": 1,
  "results": {
    "unconditional": {
      "n": 37,
      "mean_reference_net_pct": -0.23374000296215228,
      "positive_pct": 45.945945945945944
    },
    "momentum20": {
      "n": 24,
      "mean_reference_net_pct": 0.42516838447158484,
      "positive_pct": 50
    },
    "breakout20": {
      "n": 11,
      "mean_reference_net_pct": 1.9778334255608798,
      "positive_pct": 72.72727272727273
    }
  },
  "point_in_time_verified": false,
  "production_eligible": false
}
```
