# Steps 80–81 — Source-verified pilot evidence and controlled replay

## Step 80 — source coverage and historical pilot evidence
- Add a reviewed provider catalog for NEPSE Official, CDSC, ShareSansar, Chukul, ShareHub Nepal, Punji, Merolagani, NepseAlpha, ChartNepali and Bullhouse Investment.
- Treat NEPSE/CDSC as primary evidence candidates and third-party providers as corroboration only. The catalog does not authenticate any publisher.
- Require explicit operator-reviewed source contracts, exact HTTPS host allowlists, authority and licence review, pagination contracts and external secret references before capture.
- Require archived raw payload hashes, positive row counts, complete pagination, schema validation, capture windows, publisher identity and all approved-source captures.
- Require independent reconciliation, zero unresolved critical anomalies, verified official session calendar and point-in-time universe including IPO/delist/suspension coverage.
- Punji remains identity-review-required until its legal publisher identity is confirmed; it cannot count toward independent-provider coverage before that.

## Step 81 — controlled six-scanner replay
- Gate the replay handoff on Step 80 evidence readiness.
- Continue through Steps 77–79: dataset fingerprint, corporate-action and lineage checks, chronological untouched OOS, per-observation point-in-time leakage audit, explicit human replay authorization.
- Keep six strategies × four horizons on one common immutable dataset fingerprint.
- Any missing provider capture, incomplete pagination, unresolved anomaly, incomplete calendar/universe, or missing approval blocks all replay.

## Current boundary
No endpoint was guessed, no live source was contacted, and no real historical panel was acquired by this change. Unit tests use synthetic evidence only to prove fail-closed behavior. The gate does not itself establish publisher authenticity, exchange-wide completeness, valid trading costs/fills, profitability or calibrated probabilities. A real pilot still requires operator-supplied approved contracts and raw source bundles.
