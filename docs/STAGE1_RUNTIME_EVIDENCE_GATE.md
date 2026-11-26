# Stage 1 Runtime Evidence Gate — P4.9

## Purpose

The scanner's runtime eligibility function is the final fail-closed gate between structurally valid OHLCV and research scoring. Evidence asserted by a user-upload label is not sufficient. Only rows matched to the server/deployment-owned canonical reviewed-row manifest can pass.

## Required evidence for every symbol/session row

| Gate | Required fields | Pass condition |
|---|---|---|
| Security identity | `symbol`, `date`, `security_id` | Exact symbol/date key match; nonblank current security ID |
| Instrument/lifecycle | `instrument_type`, `security_status`, `lifecycle_evidence_id` | Explicit `equity`, `active`, lifecycle evidence reference present |
| Exchange session | `session_status`, `session_evidence_id` | `verified_open` or `verified_exceptional_open`; dated evidence reference |
| Source provenance | `source_id`, `evidence_id`, `source_payload_sha256` | Approved source allowlist, nonblank evidence reference, valid SHA-256 |
| Price basis | `price_basis_reviewed`, `price_basis_status` | Literal boolean true and `verified_unadjusted_no_actions` or `verified_adjusted` |
| Corporate actions | `corporate_action_status`, `corporate_action_evidence_id` | `clear` or `adjusted_verified`, with review evidence |
| Point-in-time | `available_at` | Timezone-aware ISO-8601 timestamp no later than decision time |
| OHLCV binding | `open/high/low/close/volume` | Reviewed values exactly equal the row being assessed; structural OHLCV checks pass |

## Failure behavior

- Any missing, invalid, mismatched or future-dated field blocks that row and therefore the symbol's eligibility for the requested prefix.
- Error reasons are explicit and attached to the session date.
- No missing field is silently treated as neutral, cleared, or verified.
- Uploading CSV data does not create reviewed evidence.
- The canonical manifest loader applies the same runtime gate as the API and rejects incomplete promoted records.
- The current canonical reviewed-row manifest has zero records. Therefore this change intentionally does not make any current security eligible.

## Scope and limitations

This gate validates evidence references and row-level consistency; it does not independently fetch source documents or certify their truth. The separate upstream lifecycle, session-calendar, source-reconciliation, corporate-action and price-basis review processes must create the canonical manifest only after their own validation. The current secondary-provider 281-equity universe remains a candidate universe, not an authoritative exchange membership record.

No BUY/SELL signal, trade plan, ranking eligibility, backtest result, or production promotion is authorized by this gate.
