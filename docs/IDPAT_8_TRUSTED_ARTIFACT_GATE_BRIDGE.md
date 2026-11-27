# IDPAT-8 — Server-side trusted artifact gate bridge

## Implemented
- Connects the existing deployment-pinned TrustedArtifactStore to the IDPAT seven-gate evidence derivation.
- Loads ten server-registry modules: market health, index, sector, broker profiles, broker-sector rotation, OHLCV quality, turnover quality, execution readiness, corporate actions and source quality.
- Combines the correct artifacts into seven gates and retains every contributing source/evidence ID in a lineage trace.
- The underlying store verifies payload SHA-256, server registry metadata, finality, coverage, availability cutoff, calendar identity and applicable corporate-action, sector-membership and broker-mapping context.
- Missing, rejected, late, hash-mismatched or conflicting artifact fields block the dependent gate.
- The bridge is backend-only and accepts a TrustedArtifactStore instance, not request JSON.

## Evidence contract
Gate-specific thresholds and required fields remain defined centrally in idpat_source_evidence.py. The artifact payloads must contain the report fields required by those definitions. The deployment registry is trusted configuration and must be write-restricted to the source-ingestion/approval process.

## Limitations
- No live NEPSE feed or official data is created by this code.
- A correctly hashed artifact is not automatically an authentic exchange record; source validation, finality, rights and independent review remain required.
- No BUY/SELL/HOLD or production promotion is enabled.
