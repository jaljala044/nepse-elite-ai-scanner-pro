# IDPAT-6 — Trusted Source Evidence Adapters

Branch: idpat-6-source-evidence-adapters

## Purpose
Derive the seven IDPAT scanner gates from validated backend report envelopes, rather than accepting a browser/client's asserted `status=verified` as proof.

## Implemented
- `backend/app/idpat_source_evidence.py` defines a strict report contract for market, sector, broker, liquidity, execution, corporate actions and source quality.
- Every report must be marked `report_status=validated`, identify source_id/evidence_id and have timezone-aware available_at no later than the decision cutoff.
- Gate-specific evidence is mandatory:
  - Market: index integrity, verified session calendar and finality attestation.
  - Sector: verified membership and sector data, >=98% price coverage.
  - Broker: reconciliation and identity policy passed, >=95% verified amount coverage.
  - Liquidity: OHLCV integrity and turnover verified, >=98% per-security coverage.
  - Execution: verified session calendar, execution constraints and next-session history.
  - Corporate actions: verified registry, universe completeness and point-in-time eligibility.
  - Source quality: raw hashes, lineage, rights clearance and zero unresolved conflicts.
- Missing, stale, unvalidated or below-threshold evidence blocks the corresponding gate.
- Returns gate attestations with provenance for the existing IDPAT bundle builder. Does not enable production scoring or trading.

## Integration boundary
This adapter is a backend-only contract. Its inputs must be produced by trusted server-side validators after they inspect raw manifests, reports and hashes. A client-supplied JSON object is not trusted merely because it has these fields.
The current IDPAT HTTP request still accepts caller-supplied gate evidence for compatibility; this evidence is not independently authenticated. The next integration must replace that path with server-generated reports from the actual data stores before allowing risk planning or persistence over HTTP.

## Current source reality
No canonical, exchange-certified dataset is newly promoted by this change. Existing project audits document outstanding calendar, OHLCV, source-rights, floorsheet and security-universe gaps. Synthetic tests prove only the adapter contract.
