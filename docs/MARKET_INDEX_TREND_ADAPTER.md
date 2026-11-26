# Verified NEPSE index trend adapter

## Purpose
Produces the 25% index-trend input for the evidence-gated market health
classifier. It returns a 0-100 rules-based descriptor only when the complete
requested benchmark window is supported by verified, final, point-in-time
NEPSE index OHLCV.

## Admission contract
- Caller supplies the independently verified, ascending NEPSE exchange-session
  calendar; calendar dates are never inferred from candle rows.
- At least 220 exact sessions are required (200-session averages plus a
  20-session comparison for the 200-session average slope).
- Each required row must be `record_type=index_ohlcv`, `index_code=NEPSE`,
  `source_validation_status=verified`, and `finality_status=final`.
- Each row needs valid OHLC, a nonblank immutable source ID, a 64-character
  SHA-256 payload digest, and timezone-aware `available_at` no later than the
  decision timestamp.
- Missing, provisional, malformed, future, or provenance-incomplete rows
  withhold the entire score. Duplicate sessions raise an error.
- The adapter does not assign verification status or choose between conflicting
  third-party archives.

## Score (descriptive, not probability)
| Check | Points |
|---|---:|
| Close above SMA20 | 15 |
| SMA20 above SMA50 | 20 |
| SMA50 above SMA200 | 25 |
| SMA200 rising versus its value 20 sessions earlier | 20 |
| Positive 21-session return | 10 |
| Positive 63-session return | 10 |

Only true checks contribute. The resulting component shape contains
`status=verified`, `score`, `as_of_session`, `source_id`, and
`source_payload_sha256`, matching the market-health component contract.
The output is descriptive market context and cannot authorize a stock BUY.

## Current data limitation
The repository's observed index-date reconciliation records show unresolved
primary-exchange evidence gaps and numeric differences against the YONEPSE
third-party mirror. Those candidate rows are not admitted by this adapter.
Therefore synthetic tests establish code behavior only; they do not create a
verified live NEPSE trend score. The market-health input remains unavailable
until an independently validated exchange dataset and session calendar pass
the admission contract.
