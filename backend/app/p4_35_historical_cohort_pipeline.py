"""Steps 100-109: deterministic source normalization and cohort qualification."""
from __future__ import annotations
from collections import defaultdict
from datetime import date
from math import isfinite
from typing import Any

def normalize_ohlcv(records: list[dict[str,Any]], *, provider_id: str) -> dict[str,Any]:
    normalized=[]; rejected=[]
    for i,row in enumerate(records):
        try:
            symbol=str(row["symbol"]).strip().upper()
            session=date.fromisoformat(str(row["session_date"])).isoformat()
            values={k:float(row[k]) for k in ("open","high","low","close","volume")}
            if not symbol or any(not isfinite(v) for v in values.values()): raise ValueError("invalid_symbol_or_non_finite")
            if min(values.values())<0 or values["low"]>min(values["open"],values["close"]) or values["high"]<max(values["open"],values["close"]) or values["low"]>values["high"]: raise ValueError("invalid_ohlcv_relationship")
            normalized.append({"symbol":symbol,"session_date":session,**values,"provider_id":provider_id})
        except (KeyError,ValueError,TypeError) as exc:
            rejected.append({"row_index":i,"reason":str(exc)})
    return {"records":normalized,"rejected":rejected,"accepted_count":len(normalized),"rejected_count":len(rejected)}

def detect_duplicate_sessions(records: list[dict[str,Any]]) -> list[dict[str,Any]]:
    seen=defaultdict(list)
    for i,r in enumerate(records): seen[(r.get("symbol"),r.get("session_date"))].append(i)
    return [{"symbol":k[0],"session_date":k[1],"row_indices":v} for k,v in seen.items() if len(v)>1]

def compare_provider_sessions(records: list[dict[str,Any]], *, fields: tuple[str,...]=("open","high","low","close","volume")) -> list[dict[str,Any]]:
    groups=defaultdict(list)
    for r in records: groups[(r.get("symbol"),r.get("session_date"))].append(r)
    out=[]
    for (symbol,session),rows in sorted(groups.items()):
        if len({r.get("provider_id") for r in rows})<2: continue
        conflicts={f:sorted({r.get(f) for r in rows},key=lambda x:str(x)) for f in fields if len({r.get(f) for r in rows})>1}
        out.append({"symbol":symbol,"session_date":session,"provider_count":len({r.get("provider_id") for r in rows}),"conflicts":conflicts,"status":"CONFLICT_REVIEW" if conflicts else "MATCHED"})
    return out

def find_missing_sessions(records: list[dict[str,Any]], expected_sessions: list[str], *, symbol: str) -> list[str]:
    present={r.get("session_date") for r in records if r.get("symbol")==symbol}
    return [s for s in expected_sessions if s not in present]

def validate_security_mapping(*, symbol: str, security_id: str | None, effective_from: str | None,
                              effective_to: str | None, evidence_refs: list[str]) -> dict[str,Any]:
    try:
        start=date.fromisoformat(effective_from) if effective_from else None
        end=date.fromisoformat(effective_to) if effective_to else None
        if start and end and end<start: raise ValueError("effective_date_order_invalid")
        valid=bool(symbol.strip() and security_id and start and evidence_refs)
        return {"symbol":symbol.upper(),"security_id":security_id,"effective_from":effective_from,
                "effective_to":effective_to,"evidence_refs":evidence_refs,
                "status":"EVIDENCE_BACKED_CANDIDATE" if valid else "UNRESOLVED",
                "production_identity_approved":False}
    except ValueError as exc:
        return {"symbol":symbol.upper(),"status":"BLOCKED","errors":[str(exc)],"production_identity_approved":False}

def build_cohort_quality_report(*, records: list[dict[str,Any]], expected_sessions: list[str],
                                required_symbols: list[str], minimum_session_coverage: float=0.98) -> dict[str,Any]:
    duplicates=detect_duplicate_sessions(records)
    comparisons=compare_provider_sessions(records)
    symbol_reports=[]
    for symbol in required_symbols:
        missing=find_missing_sessions(records,expected_sessions,symbol=symbol)
        coverage=(len(expected_sessions)-len(missing))/len(expected_sessions) if expected_sessions else 0.0
        symbol_reports.append({"symbol":symbol,"expected_sessions":len(expected_sessions),
          "missing_sessions":missing,"coverage_ratio":round(coverage,6),
          "status":"QUALIFIED_FOR_REVIEW" if coverage>=minimum_session_coverage and not duplicates else "BLOCKED"})
    conflicts=[c for c in comparisons if c["status"]=="CONFLICT_REVIEW"]
    ready=bool(symbol_reports) and not duplicates and not conflicts and all(s["status"]=="QUALIFIED_FOR_REVIEW" for s in symbol_reports)
    return {"status":"COHORT_QUALIFIED_FOR_REVIEW" if ready else "BLOCKED",
      "record_count":len(records),"duplicate_sessions":duplicates,"provider_comparisons":comparisons,
      "conflicts":conflicts,"symbols":symbol_reports,
      "production_admission_allowed":False,"scanner_activation_allowed":False}
