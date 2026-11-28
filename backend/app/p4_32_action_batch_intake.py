"""Step 97: batch corporate-action intake manifest and coverage report."""
from __future__ import annotations
from collections import defaultdict
from typing import Any

def build_action_batch_report(*, source_files: list[dict[str, Any]], required_action_ids: list[str]) -> dict[str, Any]:
    """Summarize independently validated CSV intake results without approving events."""
    by_action: dict[str,list[dict[str,Any]]]=defaultdict(list)
    file_errors=[]
    accepted_rows=0
    for item in source_files:
        intake=item.get("intake_result") or {}
        if intake.get("status")!="CSV_INTAKE_VERIFIED":
            file_errors.append({"source_id":item.get("source_id"),"reason":"source_csv_not_verified"})
            continue
        for row in intake.get("records",[]):
            by_action[str(row.get("action_id",""))].append(row)
            accepted_rows+=1
    events=[]
    for action_id in sorted(set(required_action_ids)):
        rows=by_action.get(action_id,[])
        publishers={str(r.get("publisher_id","")) for r in rows if r.get("publisher_id")}
        primary=any(r.get("source_tier")=="primary_nepse_or_cdsc" for r in rows)
        fact_sets={(r.get("symbol"),r.get("security_id"),r.get("action_type"),r.get("announced_at"),
                    r.get("available_at"),r.get("ex_date"),r.get("status"),
                    r.get("adjustment_factor"),r.get("factor_methodology_id")) for r in rows}
        conflict=len(fact_sets)>1
        ready=bool(rows) and len(publishers)>=2 and primary and not conflict
        blockers=[]
        if not rows: blockers.append("no_verified_source_assertions")
        if len(publishers)<2: blockers.append("two_distinct_publishers_required")
        if not primary: blockers.append("primary_nepse_or_cdsc_required")
        if conflict: blockers.append("source_fact_conflict_requires_manual_resolution")
        events.append({"action_id":action_id,"assertion_count":len(rows),"publishers":sorted(publishers),
                       "primary_present":primary,"conflict":conflict,
                       "status":"REVIEW_READY" if ready and not file_errors else "BLOCKED",
                       "blockers":blockers})
    return {"status":"REVIEW_READY" if events and all(e["status"]=="REVIEW_READY" for e in events) and not file_errors else "BLOCKED",
            "source_file_count":len(source_files),"accepted_assertion_count":accepted_rows,
            "file_errors":file_errors,"events":events,"corporate_action_admission_allowed":False,
            "adjustment_factor_approval_allowed":False,"ohlcv_mutation_allowed":False}
