# NEPSE benchmark admission gate for relative strength

The feature pipeline recognizes only records with this explicit contract:

| Field | Required value / meaning |
|---|---|
| `record_type` | `index_ohlcv` |
| `index_code` | `NEPSE` |
| `session_date` | Valid ISO exchange-session date |
| `close` | Finite positive final index close |
| `available_at` | Timezone-aware publication/availability timestamp; must be <= decision time |
| `source_validation_status` | `verified` only after source/session/row checks |
| `finality_status` | `final`; provisional rows are withheld |
| `source_id` | Nonblank immutable source identifier |
| `source_payload_sha256` | 64-character SHA-256 of the captured source payload |

The pipeline does not fetch a benchmark automatically and does not mark records
verified. The upstream acquisition/audit process is responsible for preserving
raw bytes, request/response metadata, source revision, TLS/provenance details,
session evidence, duplicate/conflict checks, finality and source hash before
assigning the verification status.

## Current source disposition

- YONEPSE is a third-party mirror attributing recent history to the NEPSE API.
  Its publisher code has documented TLS certificate verification disabled;
  it remains corroboration, not a sole canonical benchmark source.
- SocrateAI's dated index archive has known exact/conflicting duplicate rows and
  an OHLC-bound anomaly. Those rows remain quarantined until independently
  resolved; do not choose a row or apply tolerance corrections automatically.
- The official NEPSE index-history endpoint is identified as
  `/api/nots/index/history/58`, but the current project evidence does not yet
  establish a fully captured, date-complete, independently reconciled and
  production-approved history for all required 1W/1M/3M/6M windows.

Therefore the 15% RS component remains null unless the caller supplies rows
that have passed the explicit admission contract. A passing synthetic test
only proves the adapter mechanics; it is not a live benchmark data validation.

## Relative-strength alignment

All equities must have a close on the latest verified final benchmark date and
on every exact benchmark date in each 5/21/63/126-session window. The engine
does not forward-fill, interpolate, use stale endpoints, or silently shorten a
window. Missing dates exclude that symbol from the RS cross-section with a
reason. Percentile ranks are calculated only across symbols with all four
horizons available.

No BUY recommendation may be based on RS alone. The V3 coverage and Stage-1
quality gates remain authoritative.
