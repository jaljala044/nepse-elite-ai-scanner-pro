# 3B.01 — Signal confirmation engine

## Rule set

A bullish confirmation requires all of:
1. Latest close above the prior 20-session high (latest candle excluded).
2. Latest close above SMA20 and SMA50.
3. SMA20 above SMA50.
4. Latest volume at least 1.5 times the prior 20-session average.
5. Latest close in the upper 25% of its candle range.

A bearish warning is the symmetric downside pattern: close below the prior
20-session low and both moving averages, SMA20 below SMA50, volume expansion,
and a close in the lower 25% of the candle. It is not a short-sale instruction.

## Fail-closed behavior

The caller must pass `eligible=True` only after the server-owned review gate
has certified row identity, lifecycle, session, provenance, corporate-action
and point-in-time availability. The default is false. Invalid or insufficient
input returns UNKNOWN.

## Output classes

- `bullish_confirmation`: all bullish rules passed.
- `bearish_warning`: all bearish rules passed.
- `no_confirmation`: eligible data, neither full rule set passed.
- `UNKNOWN`: eligibility or structural validation unavailable.
- `insufficient_data`: fewer than 55 observations.

## Limitations

Daily OHLCV only. No intraday confirmation, order book, verified broker flow,
sector/market regime, liquidity, slippage, transaction costs or out-of-sample
backtest. Thresholds are research defaults, not calibrated probabilities.
No BUY/SELL/HOLD/NO TRADE, entry, stop, target, sizing, alert or order is emitted.

## Tests

From `backend/`: `python -m unittest tests.test_signal_confirmation`

## Real-data acceptance status (2026-11-27)

The feature is implemented and its automated tests cover deterministic synthetic
patterns. That is software verification, not market-history validation.

The repository's official per-security history review window
(`2026-10-05` through `2026-11-26`) contains 29 reported session dates and
281 current-equity candidate crosswalk matches. Its audit explicitly sets
`canonical_promotion_allowed=false`,
`coverage_admission_allowed=false`, and
`historical_security_identity_verified=false`. The per-security history
payloads provide date, trades, volume, turnover, high, low and close; they do
not provide the complete open/high/low/close/volume row required by this
engine. The captured window is also shorter than the engine's 55-observation
default.

The server-owned canonical reviewed-row manifest
(`data/reference/scanner_canonical_reviewed_rows.json`) currently contains
zero records. The ShareSansar archive already in this project is secondary
evidence and its own manifest prohibits promotion/training. Neither source may
be used to bypass the server eligibility gate.

### Additional source investigation (2026-11-27)

A public NEPSE data-pipeline project reports that NEPSE's per-security EOD
history API returns complete daily OHLCV but is server-limited to a rolling
365-day window. Its published research dataset keeps this official-source
table separate from a longer ShareSansar-derived history; the project reports
a 226-day overlap with 75,671 matched rows and exact volume agreement, but
explicitly says the pre-2025 history is not independently verified. The same
pipeline documents a WASM-derived token/access-control mechanism and describes
the legality of working around it as uncertain. We will not copy that
authentication workaround, scrape around access controls, or import its
third-party data as canonical reviewed evidence:
https://huggingface.co/datasets/AnkitSanjyal/nepse-market-data

A second public archive claims 3,600 sessions from 2011 onward and publishes
complete daily OHLCV CSVs. Its README is unusually transparent: it says the
archive is scraped from ShareSansar (not NEPSE directly), describes public
publication as a redistribution decision rather than a settled right, and
states the data is not covered by its MIT code licence. It also documents
unresolved source days and says no adjustment for bonus shares, rights issues
or splits is applied. This is useful provenance/coverage research, but it is
not independent exchange evidence, does not establish our right to ingest or
redistribute the data, and does not satisfy the corporate-action and source
rights review required by our canonical gate:
https://github.com/srijankarki07/nepse-data

A separate commercial API vendor, Share Hub, documents an all-time per-stock
daily OHLCV history service. Access requires a vendor-issued Data API account,
a server IP allow-list, and the relevant licensed package. Its docs describe
bearer-token authentication, per-licence rate limits, and a test mode that the
vendor must enable:
https://sharehubnepal.com/data/nepse-data-documentation/
This is the strongest currently documented procurement/integration route, but
it is not presently available to this repository: no account, test-mode
enablement, licence, credentials, or rights grant is present. We will not
attempt unauthenticated calls, guess credentials, or treat documentation as
proof of entitlement.

### Source decision and next acceptance path

- Do not ingest either ShareSansar-derived archive into the canonical reviewed
  manifest. Their common upstream is not independent confirmation; publication
  does not grant this project data rights.
- Do not reverse-engineer or bypass NEPSE's token/access controls.
- The direct official-source route remains the preferred route if NEPSE
  provides an authorized capture method and adequate history. A rolling
  365-day window could support a 55-session test, but the source must first be
  accessed lawfully and the capture independently reviewed.
- The practical alternative is a licensed Share Hub account with price-history
  service enabled and this project's server IP allow-listed. Only after access
  and permitted-use terms are established should an adapter capture data into
  quarantine for row-level reconciliation, identity/lifecycle review,
  corporate-action checks, and canonical admission.
- No external data has been imported or promoted by this investigation.

### Acceptance decision

- Implementation and synthetic unit/API tests: complete.
- Latest verified code CI (commit `28fed929`): 2/2 workflows passed.
- Documentation-only follow-up commit: CI result pending/none reported yet.
- Production-reviewed historical rows: unavailable.
- Real-market backtest and out-of-sample calibration: not performed.
- Production signal eligibility: not granted.
- PR remains open and unmerged pending the project's normal review.

Do not mark this feature fully validated, production-ready, or performance-
tested until a sufficiently long, complete, independently reviewed OHLCV
history is admitted through the canonical evidence process.
