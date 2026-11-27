"""Trusted-input orchestration for NEPSE source admission and history review."""
from __future__ import annotations
from app.canonical_reconciliation import reconcile_ohlcv_batches
from app.historical_coverage_validation import validate_120_session_history

_REQUIRED = ("source_id", "available_at", "rights_status", "source_validation_status",
             "finality_status", "raw_sha256", "independence_group", "independence_review_status")

def build_nepse_evidence_pipeline(*, reference_admission, admitted_batches, expected_pairs,
    decision_cutoff, ledger_available_at, security_universe, verified_sessions,
    corporate_action_reviews, adjustment_basis="raw", lookback_sessions=120,
    minimum_coverage=0.98, minimum_independent_sources=2):
    """Join successful raw CSV admissions to independent reconciliation and history gates."""
    errors, batches, source_evidence, seen = [], [], {}, set()
    if not isinstance(reference_admission, dict) or reference_admission.get("research_review_allowed") is not True:
        errors.append("official_reference_evidence_not_admitted_for_research")
    if not isinstance(admitted_batches, list) or not admitted_batches:
        errors.append("admitted_source_batches_missing")
    for i, item in enumerate(admitted_batches if isinstance(admitted_batches, list) else []):
        if not isinstance(item, dict):
            errors.append(f"batch_{i}_invalid"); continue
        admission, manifest = item.get("admission"), item.get("manifest")
        if not isinstance(admission, dict) or admission.get("admission_allowed") is not True:
            errors.append(f"batch_{i}_raw_admission_not_approved"); continue
        if not isinstance(manifest, dict):
            errors.append(f"batch_{i}_capture_manifest_missing"); continue
        missing = [k for k in _REQUIRED if not manifest.get(k)]
        if missing:
            errors.append(f"batch_{i}_manifest_fields_missing:" + ",".join(missing)); continue
        sid = manifest["source_id"]
        if sid in seen:
            errors.append(f"duplicate_source_batch:{sid}"); continue
        seen.add(sid)
        if admission.get("source_id") != sid or admission.get("raw_sha256") != manifest.get("raw_sha256"):
            errors.append(f"batch_{i}_admission_manifest_mismatch"); continue
        if admission.get("production_promotion_allowed") is not False:
            errors.append(f"batch_{i}_promotion_policy_not_fail_closed"); continue
        rows = admission.get("rows")
        if not isinstance(rows, list) or not rows:
            errors.append(f"batch_{i}_admitted_rows_missing"); continue
        source = {k: manifest[k] for k in _REQUIRED}
        source_evidence[sid] = source
        batches.append({**source, "rows": [r for r in rows if isinstance(r, dict) and r.get("status") == "valid_candidate"]})
    ledger = reconcile_ohlcv_batches(batches=batches, expected_pairs=expected_pairs,
        decision_cutoff=decision_cutoff, minimum_independent_sources=minimum_independent_sources)
    history = validate_120_session_history(reconciliation_ledger=ledger,
        ledger_available_at=ledger_available_at, source_evidence=source_evidence,
        security_universe=security_universe, verified_sessions=verified_sessions,
        corporate_action_reviews=corporate_action_reviews, decision_cutoff=decision_cutoff,
        lookback_sessions=lookback_sessions, minimum_coverage=minimum_coverage,
        adjustment_basis=adjustment_basis, minimum_independent_sources=minimum_independent_sources)
    errors.extend(ledger.get("reasons", [])); errors.extend(history.get("errors", []))
    errors = list(dict.fromkeys(errors))
    allowed = (not errors and isinstance(reference_admission, dict)
        and reference_admission.get("research_review_allowed") is True
        and ledger.get("status") == "research_only_reconciled"
        and history.get("research_review_allowed") is True)
    return {"status": "nepse_history_ready_for_research_review" if allowed else "nepse_history_blocked_or_incomplete",
        "reference_admission_status": reference_admission.get("status") if isinstance(reference_admission, dict) else None,
        "source_batch_count": len(admitted_batches) if isinstance(admitted_batches, list) else 0,
        "verified_source_count": len(batches), "reconciliation_ledger": ledger,
        "historical_coverage": history, "errors": errors, "research_review_allowed": allowed,
        "production_promotion_allowed": False,
        "policy": "trusted_raw_admission_then_independent_reconciliation_then_120_verified_sessions_no_gap_fill_no_production"}
