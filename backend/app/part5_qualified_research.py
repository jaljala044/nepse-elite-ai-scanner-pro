"""Qualified research only; never writes or substitutes canonical evidence."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from .point_in_time import _aware
from .scanner import quality_errors

RESEARCH_PROVIDERS=frozenset({"sharehub","nepsealpha","chukul","sharesansar","punji","nepse_trading","merolagani","nepse"})
FIELDS=("open","high","low","close","volume","turnover")
CONSENSUS_PROVIDERS=frozenset({"sharehub","nepsealpha","chukul","sharesansar","punji","merolagani"})

def reconcile_field(records, *, symbol, session_date, field, semantics):
    """Exact agreement only; unknown/access-blocked records are not votes."""
    if field not in FIELDS or not semantics:
        raise ValueError("explicit field semantics required")
    date.fromisoformat(session_date)
    votes={}
    excluded=[]
    for row in records:
        provider=row.get("provider")
        try:
            if provider not in RESEARCH_PROVIDERS or row.get("symbol")!=symbol or row.get("date")!=session_date:
                raise ValueError("identity_or_provider")
            if row.get("status")!="captured" or row.get("field")!=field or row.get("semantics")!=semantics:
                raise ValueError("capture_or_semantics")
            if not re.fullmatch(r"[0-9a-f]{64}",row.get("sha256","")) or not row.get("evidence_uri"):
                raise ValueError("provenance")
            _aware(row["retrieved_at"])
            value=Decimal(str(row["value"]))
            if not value.is_finite() or value<0 or (field in FIELDS[:4] and value<=0) or (field=="volume" and value!=value.to_integral_value()):
                raise ValueError("invalid_value")
            lineage=row.get("lineage") if row.get("lineage_reviewed") is True else None
            vote=(value,lineage)
            if provider in votes and votes[provider]!=vote:
                return {"status":"conflict","value":None,"production_eligible":False}
            votes[provider]=vote
        except (ValueError,TypeError,KeyError,InvalidOperation,AttributeError):
            excluded.append(provider)
    values={v[0] for v in votes.values()}
    eligible={p:v for p,v in votes.items() if p in CONSENSUS_PROVIDERS}
    lineages={v[1] for v in eligible.values() if isinstance(v[1],str) and v[1].strip()}
    consensus=len(values)==1 and len(eligible)>=4 and len(lineages)>=2
    status="conflict" if len(values)>1 else ("verified_secondary_consensus" if consensus else ("qualified_single_or_partial_source" if values else "missing"))
    return {"status":status,"value":str(next(iter(values))) if len(values)==1 else None,
            "providers":sorted(votes),"excluded":excluded,"independent_lineages":len(lineages),
            "production_eligible":False}

def qualified_segment(rows, *, expected_sessions, source_id, source_uri, source_sha256, price_basis, availability_assumption=None):
    """Retrospective research admission, not a certified point-in-time replay."""
    reasons=quality_errors(rows)
    sessions=list(expected_sessions)
    if not sessions or sessions!=sorted(set(sessions)) or [str(r.get("date")) for r in rows]!=sessions:
        reasons.append("missing_duplicate_or_unexpected_sessions")
    if source_id not in RESEARCH_PROVIDERS or not source_uri or not re.fullmatch(r"[0-9a-f]{64}",source_sha256 or ""):
        reasons.append("source_provenance_missing")
    if price_basis not in ("raw","adjusted","provider_reported_unknown"):
        reasons.append("price_basis_missing")
    if not availability_assumption:
        reasons.append("availability_assumption_missing")
    return {"qualified_research_eligible":not reasons,"reasons":reasons,
            "confidence":"LOW","classification":"retrospective_exploratory_only",
            "point_in_time_verified":False,"production_eligible":False,
            "source_id":source_id,"source_uri":source_uri,"source_sha256":source_sha256,
            "price_basis":price_basis,"availability_assumption":availability_assumption,
            "limitations":["Provider and calendar claims supplied by caller; source rights and lifecycle not independently verified.",
                           "Unknown corporate-action basis can distort returns; no production or training admission."]}
