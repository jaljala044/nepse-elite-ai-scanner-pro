# Steps 56–57 — source reconciliation and replay preflight

## Step 56: operator-supplied official source reconciliation

Added `backend/app/historical_pilot_reconciliation.py`. It validates each required capture artifact against the approved registry, rechecks exact raw payload hashes, flags missing/failed/duplicate capture IDs, and runs official first-contract evidence against each cohort symbol's reported first-trade boundary. It keeps capture completeness, first-trade agreement, publisher authenticity and exchange completeness as distinct claims.

No network connector or endpoint was guessed. The workflow consumes exact raw bytes/manifests supplied by an operator. If no real artifacts are supplied, the result remains BLOCKED.

## Step 57: deterministic panel and replay preflight

Added `backend/app/historical_pilot_replay_gate.py`. It calls the validated panel assembler and admission gate, then produces a canonical JSON SHA-256 dataset manifest. The preflight can report bounded-research readiness, but it does not promote the panel, authorize backtesting or execute a replay. Those require independent human review and explicit dataset admission.

## Evidence boundary

Tests use synthetic fixtures only. No official NEPSE/CDSC data, SAIL first-day record or verified market-wide calendar was acquired in this work. No historical replay, strategy performance, scanner accuracy or trading probability is claimed. Production remains disabled.
