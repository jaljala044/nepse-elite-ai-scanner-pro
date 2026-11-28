# Steps 92–93 — evidence intake inventory and event-level reconciliation

## Step 92: outstanding evidence request inventory
- Convert required listing/lifecycle and corporate-action event IDs into a deterministic acquisition checklist.
- Display event type, symbol/security identifier, available artifact IDs, publisher count, primary-evidence presence and next required action.
- Missing evidence remains explicitly unresolved. The inventory never infers predecessor IDs, first-trade dates or action terms.

## Step 93: event-level source assertion matrix
- Bind each assertion to a previously verified raw artifact ID, publisher and exact SHA-256.
- Enforce point-in-time availability and timezone-aware timestamps.
- Compare symbol/security ID, action type, announcement/effective/ex-dates, status, factor and factor methodology across publishers.
- Surface conflicts; do not average or silently select one source.
- Require two distinct publishers including primary NEPSE/CDSC evidence for review readiness.

## Boundaries
- Review readiness is not historical-universe admission or corporate-action approval.
- This implementation does not fetch sources, establish publisher authenticity, compute adjustment factors, mutate OHLCV or enable live signals.
- Real PDF/HTML/CSV exports and capture manifests remain required. Synthetic tests prove validator behavior only.
