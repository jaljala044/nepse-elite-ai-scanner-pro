# Steps 110–119 — BENH capture and predecessor identity

| Step | Delivery |
|---|---|
| 110 | ShareHub chart-history capture adapter with raw payload SHA-256 and capture metadata |
| 111 | Chukul chart-history adapter with provider field aliases |
| 112 | ShareSansar chart-history adapter with provider field aliases |
| 113 | Invalid chart rows quarantined; accepted rows retain symbol/session/provider |
| 114 | Floorsheet trade rows aggregated to daily executions, quantity and turnover |
| 115 | Earliest chart/floorsheet comparison; mismatches remain partial evidence |
| 116 | Cross-provider OHLCV comparison and field-level conflict reporting |
| 117 | BPW predecessor identity assessment |
| 118 | JALPA predecessor identity assessment |
| 119 | KLBSL and MKLB predecessor identity assessments |

## Capture contract
Adapters process caller-supplied raw captures. They do not scrape ShareHub, Chukul or ShareSansar, and this PR does not claim that any real BENH history or floorsheet archive was downloaded. Each chart/floorsheet capture requires source URL, timezone-aware capture timestamp and raw payload; SHA-256 is retained. Provider aliases are explicit and unsupported shapes are quarantined.

## Reconciliation and identity boundaries
- Earliest chart candle, earliest observed floorsheet trade and official listing date are separate facts.
- A chart/floorsheet date mismatch is `PARTIAL_EVIDENCE`; agreement is not sufficient unless floorsheet coverage is explicitly verified.
- Provider disagreements are reported by field, not silently averaged.
- BPW, JALPA, KLBSL and MKLB are assessed independently. A symbol mapping remains unresolved without a security ID, effective date and an allowed authoritative evidence type.
- Candidate identity never means production approval. No mapping is auto-approved; no scanner activation is enabled.

Tests use synthetic fixtures only. Production admission and historical performance claims remain disabled.
