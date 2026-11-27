"""120 verified-session OHLCV coverage and corporate-action-aware admission."""
from __future__ import annotations
import hashlib, json, re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Mapping

_SHA = re.compile(r"^[0-9a-f]{64}$")
_FIELDS = ("open", "high", "low", "close", "volume", "turnover")

def _utc(value):
    if not isinstance(value, str): return None
    try: dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None
    if dt.tzinfo is None or dt.utcoffset() is None: return None
    return dt.astimezone(timezone.utc)

def _valid_values(values):
    if not isinstance(values, Mapping): return False
    try: numbers = {k: Decimal(str(values[k])) for k in _FIELDS}
    except (KeyError, InvalidOperation, TypeError, ValueError): return False
    if any(not x.is_finite() for x in numbers.values()): return False
    if any(numbers[k] <= 0 for k in ("open", "high", "low", "close", "volume")) or numbers["turnover"] < 0: return False
    return numbers["high"] >= max(numbers[k] for k in ("open","high","low","close")) and numbers["low"] <= min(numbers[k] for k in ("open","high","low","close"))

def validate_120_session_history(*, reconciliation_ledger, ledger_available_at,
                                 source_evidence, security_universe, verified_sessions,
                                 corporate_action_reviews, decision_cutoff,
                                 lookback_sessions=120, minimum_coverage=0.98,
                                 adjustment_basis="raw", minimum_independent_sources=2):
    """Validate a rolling N-session window without filling gaps or guessing actions."""
    cutoff = _utc(decision_cutoff)
    ledger_time = _utc(ledger_available_at)
    if cutoff is None or ledger_time is None: raise ValueError("cutoff_and_ledger_availability_must_be_timezone_aware")
    if ledger_time > cutoff: raise ValueError("reconciliation_ledger_available_after_cutoff")
    if isinstance(lookback_sessions, bool) or not isinstance(lookback_sessions, int) or lookback_sessions < 1:
        raise ValueError("lookback_sessions_must_be_positive_integer")
    if isinstance(minimum_independent_sources, bool) or not isinstance(minimum_independent_sources, int) or minimum_independent_sources < 2:
        raise ValueError("minimum_independent_sources_must_be_at_least_two")
    try: threshold = Decimal(str(minimum_coverage))
    except (InvalidOperation, TypeError, ValueError): raise ValueError("minimum_coverage_invalid")
    if not threshold.is_finite() or threshold <= 0 or threshold > 1: raise ValueError("minimum_coverage_out_of_range")
    if adjustment_basis not in {"raw","split_adjusted","total_return_adjusted"}: raise ValueError("adjustment_basis_invalid")

    ledger = dict(reconciliation_ledger) if isinstance(reconciliation_ledger, Mapping) else {}
    digest = ledger.get("ledger_sha256")
    body = {k:v for k,v in ledger.items() if k != "ledger_sha256"}
    actual = hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    errors = []
    if not isinstance(digest,str) or not _SHA.fullmatch(digest) or digest != actual: errors.append("reconciliation_ledger_hash_invalid")
    if ledger.get("production_promotion_allowed") is not False or ledger.get("canonical_promotion_allowed") is not False:
        errors.append("ledger_promotion_policy_not_fail_closed")

    sessions = []
    for value in verified_sessions if isinstance(verified_sessions,list) else []:
        try: day = date.fromisoformat(value).isoformat()
        except (TypeError,ValueError): errors.append("verified_session_date_invalid:"+str(value)); continue
        if day <= cutoff.date().isoformat(): sessions.append(day)
        else: errors.append("future_verified_session_excluded:"+day)
    if len(sessions) != len(set(sessions)): errors.append("duplicate_verified_sessions")
    sessions = sorted(set(sessions))[-lookback_sessions:]
    if len(sessions) < lookback_sessions: errors.append("insufficient_verified_trading_sessions")
    universe = list(security_universe) if isinstance(security_universe,list) else []
    ids, symbols = set(), set()
    for item in universe:
        if not isinstance(item,Mapping) or not isinstance(item.get("security_id"),str) or not item["security_id"].strip() or not isinstance(item.get("symbol"),str) or not item["symbol"].strip():
            errors.append("security_universe_row_invalid"); continue
        if item["security_id"] in ids or item["symbol"] in symbols: errors.append("duplicate_security_identity")
        ids.add(item["security_id"]); symbols.add(item["symbol"])
    if not ids: errors.append("security_universe_missing")
    expected_pairs = {(sid,day) for sid in ids for day in sessions}

    sources = source_evidence if isinstance(source_evidence,Mapping) else {}
    source_errors = []
    for sid, source in sources.items():
        if not isinstance(source,Mapping): source_errors.append("source_evidence_invalid:"+str(sid)); continue
        available = _utc(source.get("available_at"))
        if source.get("rights_status") != "approved" or source.get("source_validation_status") != "verified" or source.get("finality_status") != "final":
            source_errors.append("source_not_approved:"+str(sid))
        if available is None or available > cutoff: source_errors.append("source_not_point_in_time:"+str(sid))
        if not isinstance(source.get("raw_sha256"),str) or not _SHA.fullmatch(source["raw_sha256"].lower()):
            source_errors.append("source_hash_invalid:"+str(sid))

    action_reviews = corporate_action_reviews if isinstance(corporate_action_reviews,Mapping) else {}
    action_errors = []
    for security_id in ids:
        review = action_reviews.get(security_id)
        if not isinstance(review,Mapping):
            action_errors.append("corporate_action_review_missing:"+security_id); continue
        available = _utc(review.get("available_at"))
        if review.get("status") not in {"verified_no_action","verified_adjusted"}:
            action_errors.append("corporate_action_status_unverified:"+security_id)
        if review.get("adjustment_basis") != adjustment_basis:
            action_errors.append("corporate_action_adjustment_basis_mismatch:"+security_id)
        if not review.get("source_id") or not review.get("evidence_id"):
            action_errors.append("corporate_action_lineage_missing:"+security_id)
        if available is None or available > cutoff:
            action_errors.append("corporate_action_evidence_not_point_in_time:"+security_id)
        if review.get("source_id") not in sources:
            action_errors.append("corporate_action_source_missing:"+security_id)

    reconciled = ledger.get("reconciled",[]) if isinstance(ledger.get("reconciled"),list) else []
    rows_by_key, row_errors = {}, []
    for row in reconciled:
        if not isinstance(row,Mapping): row_errors.append("reconciled_row_invalid"); continue
        key=(str(row.get("security_id","")),str(row.get("session_date","")))
        if key not in expected_pairs: continue
        if key in rows_by_key:
            row_errors.append("duplicate_reconciled_security_session:"+key[0]+":"+key[1]); continue
        if row.get("status") != "cross_source_reconciled_research_only": row_errors.append("row_not_cross_source_reconciled")
        if not _valid_values(row.get("values")): row_errors.append("reconciled_ohlcv_invalid:"+key[0]+":"+key[1])
        source_ids=row.get("source_ids")
        hashes=row.get("evidence_sha256")
        if not isinstance(source_ids,list) or len(set(source_ids)) < minimum_independent_sources:
            row_errors.append("row_lacks_independent_source_ids:"+key[0]+":"+key[1])
        if not isinstance(hashes,list) or not hashes or any(not isinstance(h,str) or not _SHA.fullmatch(h.lower()) for h in hashes):
            row_errors.append("row_evidence_hashes_invalid:"+key[0]+":"+key[1])
        if isinstance(source_ids,list):
            known=[]
            for source_id in source_ids:
                source=sources.get(source_id)
                if not isinstance(source,Mapping): row_errors.append("row_source_evidence_missing:"+str(source_id)); continue
                known.append(source)
            groups={source.get("independence_group") for source in known if source.get("independence_review_status")=="approved"}
            if len(groups)<minimum_independent_sources: row_errors.append("row_independent_lineage_unverified:"+key[0]+":"+key[1])
            expected_hashes={str(source.get("raw_sha256","")).lower() for source in known}
            if set(hashes or []) != expected_hashes: row_errors.append("row_source_hash_lineage_mismatch:"+key[0]+":"+key[1])
        rows_by_key[key]=row

    missing = sorted(expected_pairs - set(rows_by_key))
    per_security=[]
    for item in sorted(universe,key=lambda x:str(x.get("security_id",""))):
        sid=item.get("security_id")
        count=sum(1 for day in sessions if (sid,day) in rows_by_key)
        ratio=count/len(sessions) if sessions else 0.0
        missing_dates=[day for day in sessions if (sid,day) not in rows_by_key]
        per_security.append({"security_id":sid,"symbol":item.get("symbol"),"expected_sessions":len(sessions),
            "reconciled_sessions":count,"coverage_ratio":ratio,"missing_sessions":missing_dates,
            "coverage_pass":bool(sessions) and Decimal(str(ratio)) >= threshold})
        if not per_security[-1]["coverage_pass"]: errors.append("security_coverage_below_threshold:"+str(sid))
    overall = len(rows_by_key)/len(expected_pairs) if expected_pairs else 0.0
    if expected_pairs and Decimal(str(overall)) < threshold: errors.append("overall_coverage_below_threshold")
    errors.extend(source_errors); errors.extend(action_errors); errors.extend(row_errors)
    errors=list(dict.fromkeys(errors))
    allowed=bool(expected_pairs) and not errors and not missing and len(sessions)==lookback_sessions
    return {
        "status":"120_session_history_ready_for_research_review" if allowed else "history_incomplete_or_quarantined",
        "lookback_sessions":lookback_sessions,"verified_session_count":len(sessions),
        "first_session":sessions[0] if sessions else None,"last_session":sessions[-1] if sessions else None,
        "security_count":len(ids),"expected_security_session_pairs":len(expected_pairs),
        "reconciled_pair_count":len(rows_by_key),"missing_pair_count":len(missing),
        "overall_coverage_ratio":overall,"per_security":per_security,
        "missing_pairs":[{"security_id":sid,"session_date":day} for sid,day in missing],
        "errors":errors,"research_review_allowed":allowed,
        "production_promotion_allowed":False,
        "policy":"120_verified_trading_sessions_point_in_time_cross_source_corporate_action_review_no_gap_fill_no_lookahead",
    }
