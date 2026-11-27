# Steps 60–61 — official capture orchestration and six-scanner replay runner

## Step 60 — registered-source capture orchestration

Added historical_pilot_capture_runner.py. It accepts only an approved registry specification, HTTPS endpoint on the exact allowlist, declared content types and an injected transport. It captures sequential pages, preserves raw bytes in the returned payload map, hashes every page, records page/availability metadata and requires an explicit terminal pagination marker. Redirects outside the approved host, late data, invalid responses, missing pagination state and page-limit exhaustion fail closed.

No NEPSE/CDSC endpoint, token, license, authentication mechanism or undocumented pagination rule is guessed. The transport must be configured by the operator to comply with publisher terms, TLS, authentication, timeouts and rate limits. Captures remain pending until they pass the existing manifest validator. Publisher authenticity and exchange completeness are not inferred.

## Step 61 — admitted six-scanner replay handoff

Added historical_pilot_replay_runner.py. It refuses execution unless Step 59 has issued explicit research admission for the exact dataset fingerprint and untouched OOS partition. It calls an injected existing replay runner for each of six strategies × four horizons, passing the same panel snapshot and SHA-256 fingerprint. It verifies strategy, horizon, partition and fingerprint in each returned run record; mismatched or failed runs remain incomplete.

This is a runner adapter, not a replacement for strategy execution logic. The injected runner must independently implement chronological walk-forward, dated costs/taxes/fees, liquidity caps, settlement delay, stop-first handling, price limits/circuit/no-bid conditions and realistic fills. No strategy metrics are interpreted and no probabilities are calibrated.

## Evidence boundary

Tests use synthetic fixtures. No official source capture has been run by this PR, no real historical panel is admitted and no OOS performance result is claimed. Actual capture requires approved source contracts, credentials/licensing where required and operator-supplied endpoint configuration.
