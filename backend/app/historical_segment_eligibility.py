"""Exploratory-only historical segment admission. Never authorizes production."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from .issue5_quarantine import Quarantine
from .quarantine_guard import is_quarantined, runtime_quarantine_keys, quarantine_gap_symbols

ARCHIVE_FIELDS = frozenset({'repository', 'commit_sha', 'source_file', 'source_file_sha256', 'target_csv_row', 'target_date'})

def day(value):
    if not isinstance(value,str) or date.fromisoformat(value).isoformat()!=value:
        raise ValueError("invalid date")
    return value

def instant(value):
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("naive timestamp")
    return dt

def evaluate_historical_segment(*,segment,expected_sessions,session_statuses,records,
                                required_sessions,available_warmup_sessions,decision_cutoff,
                                archive_guard=None, require_archive_guard=False, blocked_keys=None, session_evidence=None):
    if session_evidence is not None:
        from .historical_evidence_eligibility import evaluate_historical_segment as evidence_gate
        return evidence_gate(segment=segment, expected_sessions=expected_sessions, session_statuses=session_statuses,
                             session_evidence=session_evidence, records=records, required_sessions=required_sessions,
                             available_warmup_sessions=available_warmup_sessions, decision_cutoff=decision_cutoff,
                             archive_guard=archive_guard, require_archive_guard=require_archive_guard, blocked_keys=blocked_keys)
    reasons=[]
    traded=no_trade=0
    def reject(reason):
        if reason not in reasons:
            reasons.append(reason)
    try:
        configured = runtime_quarantine_keys()
        blocked_keys = frozenset(blocked_keys or ()) | (configured or frozenset())
    except (ValueError, TypeError):
        reject("runtime_quarantine_ledger_invalid")
        blocked_keys = frozenset()
    if segment.get("identity_verified") is not True or not segment.get("security_id") or not segment.get("symbol"):
        reject("instrument_identity_not_verified")
    if segment.get("boundary_reviewed") is not True:
        reject("lifecycle_boundary_unreviewed")
    if segment.get("suspension_overlap") is not False:
        reject("suspension_overlap_unknown_or_present")
    if segment.get("merger_or_successor_boundary") is not False:
        reject("merger_or_successor_boundary_unknown_or_crossed")
    if segment.get("adjustment_basis")!="raw":
        reject("adjustment_basis_not_verified_raw")
    try:
        cutoff=instant(decision_cutoff)
        start=day(segment["effective_from"])
        end=day(segment["effective_to"]) if segment.get("effective_to") is not None else None
        if end is not None and end<start:
            raise ValueError("inverted interval")
        sessions=[day(d) for d in expected_sessions]
        if not sessions or sessions != sorted(set(sessions)):
            reject("invalid_expected_sessions")
        if type(required_sessions) is not int or required_sessions<=0:
            raise ValueError("invalid required sessions")
        warmup=segment["minimum_warmup_sessions"]
        if type(warmup) is not int or warmup<0 or type(available_warmup_sessions) is not int or available_warmup_sessions<warmup:
            reject("insufficient_causal_warmup")
        if quarantine_gap_symbols(((str(segment.get("symbol", "")), d) for d in sessions), blocked_keys):
            reject("quarantined_session_in_window")
        expected=set(sessions)
        by_day={}
        for row in records:
            d=day(row["session_date"])
            if d in by_day:
                reject("duplicate_bar:"+d)
            by_day[d]=row
            if d not in expected:
                reject("unexpected_bar:"+d)
        for d in sorted(expected):
            if d<start or (end is not None and d>end):
                reject("session_outside_instrument_effective_interval:"+d)
            status=session_statuses.get(d)
            row=by_day.get(d)
            if status=="no_trade_verified":
                no_trade+=1
                if row is not None:
                    reject("bar_present_on_verified_no_trade_session:"+d)
                continue
            if status!="traded":
                reject("session_status_unverified:"+d)
                continue
            if row is None:
                reject("missing_bar:"+d)
                continue
            valid=True
            def bad(reason):
                nonlocal valid
                valid=False
                reject(reason+":"+d)
            if is_quarantined(row) or (str(segment.get("symbol", "")).strip().upper(), d) in blocked_keys:
                bad("quarantined_bar")
            if require_archive_guard or archive_guard is not None or ARCHIVE_FIELDS.intersection(row):
                if not isinstance(archive_guard, Quarantine):
                    bad("archive_quarantine_guard_missing")
                elif row.get("target_date") != d:
                    bad("archive_quarantine_date_binding_missing_or_mismatch")
                else:
                    disposition = archive_guard.disposition(row)
                    if disposition != "not_in_overlay_requires_other_gates":
                        bad("archive_quarantine:" + disposition)
            if row.get("symbol")!=segment.get("symbol") or row.get("security_id")!=segment.get("security_id"):
                bad("bar_identity_mismatch")
            if row.get("adjustment_basis")!=segment.get("adjustment_basis"):
                bad("bar_adjustment_basis_mismatch")
            if row.get("rights_status")!="approved":
                bad("source_rights_not_approved")
            if not re.fullmatch(r"[0-9a-fA-F]{64}",str(row.get("evidence_sha256",""))):
                bad("evidence_hash_missing_or_invalid")
            try:
                if instant(row["available_at"])>cutoff:
                    bad("lookahead_available_after_cutoff")
                if date.fromisoformat(d)>cutoff.date():
                    bad("future_session")
            except (ValueError,TypeError,KeyError,AttributeError):
                bad("availability_invalid")
            try:
                o,h,l,c,v=(Decimal(str(row[k])) for k in ("open","high","low","close","volume"))
                if not all(x.is_finite() for x in (o,h,l,c,v)) or min(o,h,l,c)<=0 or h<max(o,l,c) or l>min(o,h,c) or v<=0 or v!=v.to_integral_value():
                    bad("invalid_ohlcv")
            except (InvalidOperation,TypeError,ValueError,KeyError):
                bad("invalid_ohlcv")
            if valid:
                traded+=1
        if traded<required_sessions:
            reject("insufficient_traded_sessions")
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError):
        reject("malformed_segment_input")
    return {"exploratory_replay_eligible":not reasons,
            "approved_backtest_eligible":False,"production_promotion_allowed":False,
            "verified_traded_session_count":traded,"verified_no_trade_count":no_trade,
            "reasons":reasons}


def evaluate_archive_historical_segment(*, archive_guard=None, **kwargs):
    """Archive entry point: absence of guard/provenance always fails closed."""
    return evaluate_historical_segment(archive_guard=archive_guard, require_archive_guard=True, **kwargs)


def evaluate_runtime_historical_segment(**kwargs):
    """Require server-pinned ledger; caller exclusions cannot override it."""
    try:
        keys = runtime_quarantine_keys(required=True)
        if keys is None:
            raise ValueError("missing runtime ledger")
        kwargs["blocked_keys"] = keys | frozenset(kwargs.get("blocked_keys") or ())
    except (ValueError, TypeError):
        return {"reasons": ["runtime_quarantine_ledger_missing_or_invalid"],
                "verified_traded_session_count": 0, "verified_no_trade_count": 0,
                "exploratory_replay_eligible": False, "approved_backtest_eligible": False,
                "production_promotion_allowed": False}
    # Preserve diagnostic reasons from legacy callers, but never admit them.
    try:
        result = evaluate_historical_segment(**kwargs)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        result = {"reasons": ["malformed_runtime_evidence"], "verified_traded_session_count": 0,
                  "verified_no_trade_count": 0, "exploratory_replay_eligible": False,
                  "approved_backtest_eligible": False, "production_promotion_allowed": False}
    if not isinstance(kwargs.get("session_evidence"), dict) or not kwargs["session_evidence"]:
        result["reasons"] = sorted(set(result["reasons"]) | {"runtime_session_evidence_required"})
        result["exploratory_replay_eligible"] = False
        result["eligible_ohlcv_candle_count"] = 0
    return result
