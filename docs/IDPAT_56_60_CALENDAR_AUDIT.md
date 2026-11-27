# Calendar audit
Sample raw archive files (2024 onward candidate rule, older dates require separate review):
```json
[
  {
    "file": "ADBL_OHLCV.csv",
    "sha": "179531d7d3060e758be651a1c6ac63d3ae682eec",
    "rows": 935,
    "flagged": 243
  },
  {
    "file": "API_OHLCV.csv",
    "sha": "d29d0442bac03704a80c25c87f23ba97515a9135",
    "rows": 2520,
    "flagged": 16
  },
  {
    "file": "CFCL_OHLCV.csv",
    "sha": "c866e6fd701d34ebde97cc1ac1974bda86cb339b",
    "rows": 935,
    "flagged": 243
  },
  {
    "file": "NABIL_OHLCV.csv",
    "sha": "afd3c4568c295084500f20ab973f79865ca0ca9d",
    "rows": 936,
    "flagged": 243
  },
  {
    "file": "RHGCL_OHLCV.csv",
    "sha": "69456917ff60399f21f3ddfd374d84bb31e2f1f5",
    "rows": 957,
    "flagged": 2
  }
]
```
Candidate weekdays change April 6 2026 per data repository NEPSE_SESSION_WEEKDAY_FIX_2026-11-25.md. Counts are preliminary, not verified session conflicts; no rows removed. Backtest blocked pending canonical calendar, availability and price basis evidence.
