"""Read-only reconstruction of broker memory from quarantined-safe ledger observations.
Legacy snapshot storage remains blocked until independent rebuild validation.
"""
from datetime import datetime
from app.broker_daily_history import BrokerDailyHistoryStore
from app.broker_behavior_memory import build_broker_behavior_memory, DEFAULT_WINDOWS
from app.historical_quarantine import OVERLAY_SHA256, configured_holds, reject_held

def reconstruct_broker_memory(ledger: BrokerDailyHistoryStore, *, as_of_date: str, as_of_timestamp: str):
    if not isinstance(ledger, BrokerDailyHistoryStore):
        raise ValueError("verified_daily_ledger_required")
    cutoff = datetime.fromisoformat(as_of_timestamp.replace("Z", "+00:00"))
    if cutoff.tzinfo is None:
        raise ValueError("timezone_aware_cutoff_required")
    holds = configured_holds()
    complete = set(ledger.complete_sessions_as_of(as_of_date=as_of_date, as_of_timestamp=as_of_timestamp))
    rows = ledger.observations_as_of(as_of_date=as_of_date, as_of_timestamp=as_of_timestamp)
    observations = []
    seen = set()
    for row in rows:
        day = row["session_date"]
        if day not in complete:
            raise ValueError("observation_without_complete_session")
        reject_held(row["symbol"], day, holds)
        key = (row["security_id"], row["broker_id"], day, row["side"], row["source_id"], row["evidence_id"])
        if key in seen:
            raise ValueError("duplicate_daily_observation")
        seen.add(key)
        observations.append(dict(trade_date=day, available_at=row["available_at"],
            security_id=row["security_id"], broker_entity_id=row["broker_id"],
            identity_status="verified", session_status="verified", side=row["side"].lower(),
            amount=row["amount"], quantity=row["quantity"], coverage_ratio=row["coverage_ratio"],
            source_row_count=row["source_row_count"], source_id=row["source_id"],
            evidence_id=row["evidence_id"], source_payload_sha256=row["source_payload_sha256"]))
    built = build_broker_behavior_memory(observations, as_of_date=as_of_date)
    if built["excluded_observation_rows"]:
        raise ValueError("memory_builder_excluded_observations")
    snapshots=[]; withheld=[]
    for snap in built["memory_rows"]:
        matching=[r for r in rows if r["security_id"]==snap["security_id"] and r["broker_id"]==snap["broker_entity_id"]]
        selected_days=sorted({r["session_date"] for r in matching}, reverse=True)[:DEFAULT_WINDOWS[snap["window"]]]
        expected_days=sorted(complete,reverse=True)[:DEFAULT_WINDOWS[snap["window"]]]
        if len(expected_days)!=DEFAULT_WINDOWS[snap["window"]] or selected_days!=expected_days:
            withheld.append(dict(security_id=snap["security_id"],broker_entity_id=snap["broker_entity_id"],window=snap["window"],reason="incomplete_constituent_session_window"))
            continue
        lineage=[{k:r[k] for k in ("security_id","symbol","broker_id","session_date","side","source_id","evidence_id","source_payload_sha256","batch_id","available_at")} for r in matching if r["session_date"] in selected_days]
        snapshots.append({**snap,"constituent_sessions":sorted(selected_days),"constituent_lineage":lineage,"quarantine_overlay_sha256":OVERLAY_SHA256,"promotion_allowed":False})
    return dict(status="research_review_only", snapshots=snapshots, withheld=withheld,
        admitted_observations=len(observations), complete_sessions=len(complete),
        promotion_allowed=False, persisted=0)
