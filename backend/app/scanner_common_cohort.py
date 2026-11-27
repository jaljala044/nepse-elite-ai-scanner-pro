"""Research orchestration contract; adapters must be supplied by caller."""
from .independent_scanner_review import resolve_reviews
from .corporate_action_trade_plan import _time
METHODS=("IDPAT","WYCKOFF","SMC","BROKER","MINERVINI_MOMENTUM","MASTER")

def run_common_cohort(decisions,adapters):
    if set(adapters)!=set(METHODS): raise ValueError("six_adapters_required")
    seen=set(); output=[]
    for decision in decisions:
        key=(decision["symbol"],decision["horizon"],decision["decision_time"])
        if key in seen: raise ValueError("duplicate_decision")
        seen.add(key); cutoff=_time(key[2])
        reviews={}
        for name in METHODS:
            result=adapters[name](decision)
            if result.get("symbol")!=key[0] or result.get("horizon")!=key[1] or _time(result["available_at"])>cutoff: raise ValueError("misaligned_review")
            if not result.get("evidence_id"): raise ValueError("missing_evidence_id")
            reviews[name]=result
        directions={k:v["direction"] for k,v in reviews.items() if k!="MASTER"}
        output.append(dict(key=key,reviews=reviews,confluence=resolve_reviews(directions)))
    return dict(rows=output,decision_count=len(output),production_eligible=False,ranking=None,
        limitations=["Caller adapters and evidence identifiers are not independently verified; master excluded from independent votes."])
