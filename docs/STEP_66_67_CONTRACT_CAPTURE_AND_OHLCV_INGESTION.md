# Steps 66–67 — approved-source capture and OHLCV ingestion

## Step 66 — contract-driven capture orchestration

The new orchestration wrapper accepts only a passing Step 64 source-contract report. It forwards the exact reviewed capture specification to the existing bounded page runner, applies the approved maximum-page limit and returns the capture manifest and raw payloads for Step 65 validation. An unapproved contract never invokes the injected transport.

The transport remains operator supplied. It must enforce TLS, authentication, licence conditions, rate limiting and timeouts. The contract's minimum request interval is metadata for transport configuration; the wrapper does not sleep or independently prove that a transport honored it. Credentials remain outside the contract and repository.

## Step 67 — accepted OHLCV capture to normalized rows

A dataset-specific pipeline now joins Step 65 package acceptance with the existing strict CSV ingester. It accepts only official EOD OHLCV, requires a caller-supplied one-to-one column map, revalidates raw bytes and manifest hashes, and emits provenance-bound normalized rows. Schema inference, row repair and silent row dropping are not introduced.

The result is an ingestion report only. It is not yet a complete historical panel: permanent security identity, official open-session evidence, lifecycle intervals, corporate-action reconciliation, cross-source conflict resolution and complete symbol/session coverage remain required by the panel assembler.

## Verification boundary

Tests use synthetic fixture data and data.example.test; they do not represent live NEPSE/CDSC access. No endpoint is guessed, no network is called by the test suite, and no real dataset or strategy result is claimed. Backtest admission, canonical promotion and production remain disabled.
