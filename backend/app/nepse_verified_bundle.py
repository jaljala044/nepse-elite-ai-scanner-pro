"""Build immutable manifests from captured, validated historical NEPSE CSVs.

This orchestrates user-supplied bytes; it does not scrape or authenticate publishers.
"""
from __future__ import annotations
import hashlib, json
from app.nepse_historical_intake import ingest_captured_csv
from app.nepse_dataset_readiness import assess_historical_dataset_readiness, REQUIRED, OPTIONAL
from app.nepse_corporate_action_reconciliation import reconcile_corporate_actions

def build_verified_historical_bundle(*, captured_files, start_date, end_date,
    decision_cutoff, minimum_session_coverage_pct="100", require_optional=()):
    if not isinstance(captured_files, dict):
        raise ValueError("captured_files_mapping_required")
    unknown=set(captured_files)-set(REQUIRED)-set(OPTIONAL)
    if unknown: raise ValueError("unsupported_dataset_kind:"+",".join(sorted(unknown)))
    reports={}; file_manifest=[]
    for kind, items in sorted(captured_files.items()):
        if not isinstance(items, list): raise ValueError("captured_file_list_required:"+kind)
        reports[kind]=[]
        for index, item in enumerate(items):
            if not isinstance(item, dict): raise ValueError("captured_file_metadata_required:"+kind)
            result=ingest_captured_csv(
                raw_bytes=item.get("raw_bytes"), dataset_kind=kind,
                source_id=item.get("source_id"), publisher=item.get("publisher"),
                source_uri=item.get("source_uri"), evidence_id=item.get("evidence_id"),
                captured_at=item.get("captured_at"), decision_cutoff=decision_cutoff,
                rights_status=item.get("rights_status"), registry_review_id=item.get("registry_review_id"),
                source_validation_status=item.get("source_validation_status","verified"),
                finality_status=item.get("finality_status","final"))
            reports[kind].append(result)
            file_manifest.append({
                "dataset_kind":kind,"file_index":index,"raw_sha256":result["raw_sha256"],
                "raw_byte_count":result["raw_byte_count"],"row_count":result["row_count"],
                "source_id":result["source_envelope"]["source_id"],
                "publisher":result["source_envelope"]["publisher"],
                "evidence_id":result["source_envelope"]["evidence_id"],
                "captured_at":result["captured_at"],"status":result["status"]})
    readiness=assess_historical_dataset_readiness(intake_reports=reports,
        start_date=start_date,end_date=end_date,decision_cutoff=decision_cutoff,
        minimum_session_coverage_pct=minimum_session_coverage_pct,
        require_optional=require_optional)
    action_rows=[row for report in reports.get("corporate_actions",[])
        for row in report.get("validation",{}).get("accepted_rows",[])]
    action_reconciliation=reconcile_corporate_actions(
        action_records=action_rows,decision_cutoff=decision_cutoff)
    unresolved_actions=len(action_reconciliation.get("withheld_events",[]))+len(action_reconciliation.get("rejected_records",[]))
    # Never upgrade readiness: corporate-action conflicts downgrade assembly eligibility.
    research_allowed=(readiness.get("status")=="READY" and unresolved_actions==0)
    manifest_payload={
        "schema_version":"nepse-historical-bundle-1.0.0",
        "start_date":start_date,"end_date":end_date,"decision_cutoff":decision_cutoff,
        "files":sorted(file_manifest,key=lambda x:(x["dataset_kind"],x["raw_sha256"])),
        "readiness":readiness,"corporate_action_reconciliation":action_reconciliation,
        "research_panel_assembly_allowed":research_allowed,
        "policy":"exact captured bytes; source envelopes and point-in-time gates; duplicate and coverage validation; two-source corporate-action reconciliation; no silent adjustment or missing-data imputation"}
    canonical=json.dumps(manifest_payload,sort_keys=True,separators=(",",":"),default=str).encode()
    digest=hashlib.sha256(canonical).hexdigest()
    return {**manifest_payload,"dataset_bundle_sha256":digest,
        "bundle_status":"READY" if research_allowed else ("PARTIAL" if readiness.get("status")!="BLOCKED" else "BLOCKED"),
        "production_enabled":False,"performance_claimed":False,
        "limitations":[
            "Only captured user/provider bytes are processed; no live source download is performed.",
            "A payload hash proves byte integrity after capture, not publisher authenticity.",
            "Publisher independence, rights approval and registry review require external governance.",
            "A bundle marked READY is eligible for research assembly only, not live trading or a performance claim.",
            "No missing sessions, delisted securities or corporate actions are synthesized."]}
