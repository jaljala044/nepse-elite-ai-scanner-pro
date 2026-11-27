"""Coverage audit only; no winner or inferred trading accuracy."""
from .scanner_common_cohort import METHODS

def audit_cohort(cohort):
    counts={m:dict(bullish=0,bearish=0,neutral=0,unknown=0) for m in METHODS}
    complete=0
    for row in cohort["rows"]:
        if set(row["reviews"])!=set(METHODS): raise ValueError("incomplete_methods")
        for m in METHODS:
            direction=row["reviews"][m]["direction"].lower()
            if direction not in counts[m]: raise ValueError("invalid_direction")
            counts[m][direction]+=1
        complete+=all(row["reviews"][m]["direction"]!="UNKNOWN" for m in METHODS)
    n=len(cohort["rows"])
    return dict(decisions=n,complete_decisions=complete,coverage=counts,complete_fraction=complete/n if n else None,
        accuracy=None,winner=None,production_eligible=False)
