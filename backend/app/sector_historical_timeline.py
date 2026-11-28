"""Immutable point-in-time sector timeline keyed by stable security identity."""
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Any
from collections import defaultdict
from zoneinfo import ZoneInfo

_ALLOWED_EVENTS = {"classify", "reclassify", "symbol_change", "corporate_action_link", "close_interval"}
_ALLOWED_SOURCES = {"primary_nepse", "cdsc", "issuer", "secondary_publisher"}

def _time(value: Any, field: str) -> datetime:
    if not isinstance(value, str): raise ValueError(f"{field}_timezone_aware_required")
    try: parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: raise ValueError(f"{field}_timezone_aware_required") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None: raise ValueError(f"{field}_timezone_aware_required")
    return parsed.astimezone(timezone.utc)

def _day(value: Any, field: str) -> date:
    if not isinstance(value, str): raise ValueError(f"{field}_iso_date_required")
    try: parsed = date.fromisoformat(value)
    except ValueError: raise ValueError(f"{field}_iso_date_required") from None
    if parsed.isoformat() != value: raise ValueError(f"{field}_iso_date_required")
    return parsed

def build_sector_timeline_snapshot(events: list[dict[str, Any]], *, as_of_date: str,
        decision_time: str, allowed_sector_codes: set[str], known_security_ids: set[str]) -> dict[str, Any]:
    effective_date = _day(as_of_date, "as_of_date")
    cutoff = _time(decision_time, "decision_time")
    if effective_date > cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date():
        raise ValueError("as_of_date_after_decision_time")
    if not isinstance(events, list): raise ValueError("events_must_be_list")
    if not isinstance(allowed_sector_codes, set) or not allowed_sector_codes: raise ValueError("allowed_sector_codes_required")
    if not isinstance(known_security_ids, set) or not known_security_ids: raise ValueError("known_security_ids_required")
    visible, rejected, seen = [], [], set()
    for i, event in enumerate(events):
        if not isinstance(event, dict): raise ValueError(f"event_{i}_must_be_object")
        event_id, security_id, symbol, event_type = (event.get(k) for k in ("event_id","security_id","symbol","event_type"))
        try:
            if not isinstance(event_id,str) or not event_id.strip(): raise ValueError("event_id_required")
            if event_id in seen: raise ValueError("duplicate_event_id")
            seen.add(event_id)
            if not isinstance(security_id,str) or security_id not in known_security_ids: raise ValueError("unknown_or_unverified_security_id")
            if not isinstance(symbol,str) or not symbol.strip(): raise ValueError("symbol_required")
            symbol=symbol.strip().upper()
            if event_type not in _ALLOWED_EVENTS: raise ValueError("event_type_invalid")
            source_class=event.get("source_class")
            if source_class not in _ALLOWED_SOURCES: raise ValueError("source_class_not_admissible")
            source_id,publisher,evidence_ref,digest=(event.get(k) for k in ("source_id","publisher_id","evidence_ref","payload_sha256"))
            if not all(isinstance(x,str) and x.strip() for x in (source_id,publisher,evidence_ref)): raise ValueError("source_provenance_incomplete")
            if not isinstance(digest,str) or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest.lower()): raise ValueError("payload_sha256_invalid")
            captured=_time(event.get("captured_at"),f"event_{i}_captured_at")
            available=_time(event.get("available_at"),f"event_{i}_available_at")
            start=_day(event.get("effective_from"),f"event_{i}_effective_from")
            end=_day(event["effective_to"],f"event_{i}_effective_to") if event.get("effective_to") else None
            if available<captured: raise ValueError("available_before_capture")
            if end and end<start: raise ValueError("effective_interval_reversed")
            if captured>cutoff or available>cutoff: continue
            sector=event.get("sector_code")
            if event_type in {"classify","reclassify"} and sector not in allowed_sector_codes: raise ValueError("sector_code_invalid")
            if sector is not None and sector not in allowed_sector_codes: raise ValueError("sector_code_invalid")
            parent=event.get("supersedes_event_id")
            if parent is not None and (not isinstance(parent,str) or not parent.strip()): raise ValueError("supersedes_event_id_invalid")
            action_id=event.get("corporate_action_id")
            if event_type=="corporate_action_link" and (not isinstance(action_id,str) or not action_id.strip()): raise ValueError("corporate_action_id_required")
            visible.append({"event_id":event_id,"security_id":security_id,"symbol":symbol,"event_type":event_type,
                "sector_code":sector,"effective_from":start,"effective_to":end,"source_id":source_id,
                "publisher_id":publisher,"source_class":source_class,"evidence_ref":evidence_ref,
                "payload_sha256":digest.lower(),"supersedes_event_id":parent,"corporate_action_id":action_id})
        except ValueError as exc: rejected.append({"index":i,"event_id":event_id,"reason":str(exc)})
    ids={e["event_id"] for e in visible}
    for e in visible:
        if e["supersedes_event_id"] and e["supersedes_event_id"] not in ids:
            rejected.append({"event_id":e["event_id"],"reason":"superseded_event_not_visible_at_cutoff"})
    by_security=defaultdict(list)
    for e in visible:
        if not e["supersedes_event_id"] or e["supersedes_event_id"] in ids: by_security[e["security_id"]].append(e)
    snapshots={}
    for sid in sorted(known_security_ids):
        rows=[e for e in by_security.get(sid,[]) if e["effective_from"]<=effective_date and (e["effective_to"] is None or effective_date<=e["effective_to"])]
        classifications=[e for e in rows if e["event_type"] in {"classify","reclassify"}]
        claims=defaultdict(set)
        for e in classifications: claims[e["sector_code"]].add(e["publisher_id"])
        if not classifications: status,sector="missing_effective_classification",None
        elif len(claims)>1: status,sector="conflicting_effective_classifications",None
        else:
            candidate,publishers=next(iter(claims.items()))
            status,sector=("corroborated_research_mapping",candidate) if len(publishers)>=2 else ("single_publisher_only",None)
        symbol_events=[e for e in rows if e["event_type"]=="symbol_change"]
        symbol_claims=defaultdict(set)
        for e in symbol_events: symbol_claims[e["symbol"]].add(e["publisher_id"])
        if len(symbol_claims)>1: symbol_status,current_symbol="conflicting_symbol_aliases",None
        elif symbol_claims:
            alias,publishers=next(iter(symbol_claims.items()))
            symbol_status,current_symbol=("corroborated_symbol_alias",alias) if len(publishers)>=2 else ("single_publisher_symbol_alias",None)
        else: symbol_status,current_symbol="no_symbol_change_evidence",None
        snapshots[sid]={"status":status,"sector_code":sector,
            "classification_event_ids":sorted(e["event_id"] for e in classifications),
            "classification_publishers":sorted({e["publisher_id"] for e in classifications}),
            "symbol_status":symbol_status,"corroborated_symbol":current_symbol,
            "symbol_event_ids":sorted(e["event_id"] for e in symbol_events),
            "corporate_action_ids":sorted({e["corporate_action_id"] for e in rows if e["corporate_action_id"]}),
            "source_refs":sorted({e["evidence_ref"] for e in rows}),
            "official_membership_verified":False,"production_admission_allowed":False}
    counts=defaultdict(int)
    for item in snapshots.values(): counts[item["status"]]+=1
    return {"status":"review_ready" if snapshots and all(x["sector_code"] for x in snapshots.values()) and not rejected else "insufficient_evidence",
        "as_of_date":effective_date.isoformat(),"decision_time":cutoff.isoformat(),"security_count":len(snapshots),
        "status_counts":dict(sorted(counts.items())),"snapshots":snapshots,"rejected_events":rejected,
        "visible_event_count":len(visible),"verified":False,"admission_allowed":False,
        "score_adjustment":0,"recommendation_override":False,
        "limitations":["Stable security IDs must be independently verified and supplied by the caller.",
        "Ticker aliases and corporate-action links are evidence annotations, not inferred identity joins.",
        "Corroboration does not establish official NEPSE classification."]}
