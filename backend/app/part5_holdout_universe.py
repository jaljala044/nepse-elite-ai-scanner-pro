"""Research-only holdout and historical membership checks."""
from .point_in_time import _aware
from .part5_decision_admission import mature_training_rows

def holdout_partition(rows, *, frozen_at, holdout_start, holdout_end, evaluation_at):
    freeze,start,end,evaluation=map(_aware,(frozen_at,holdout_start,holdout_end,evaluation_at))
    if not freeze < start < end <= evaluation:
        raise ValueError("invalid holdout boundaries")
    ids=set()
    train,test,excluded=[],[],[]
    for row in rows:
        key=row["record_id"]
        if not isinstance(key,str) or not key.strip() or key in ids:
            raise ValueError("unique record ID required")
        ids.add(key)
        decision=_aware(row["decision_at"])
        if decision <= freeze:
            train.append(row)
        elif start <= decision < end:
            try:
                feature, label_end, known, issued=(_aware(row[k]) for k in
                    ("feature_available_at","label_end_at","label_available_at","forecast_issued_at"))
                valid=feature <= issued <= decision < label_end <= known <= evaluation
            except (KeyError,TypeError,ValueError,AttributeError):
                valid=False
            (test if valid else excluded).append(key)
        else:
            excluded.append(key)
    maturity=mature_training_rows(train,fit_cutoff=frozen_at,first_test_decision=holdout_start)
    return {"train_ids":maturity["included_ids"],"holdout_ids":test,
            "excluded_ids":excluded+maturity["excluded_ids"],
            "status":"research_only" if test and maturity["included_ids"] else "insufficient_sample",
            "independent_holdout_verified":False,"production_eligible":False}

def historical_membership(expected_ids, records, *, decision_at):
    """Compare against caller-supplied historical universe, never today's membership."""
    cutoff=_aware(decision_at)
    expected=list(expected_ids)
    if any(not isinstance(k,str) or not k.strip() for k in expected) or len(set(expected))!=len(expected):
        raise ValueError("invalid expected IDs")
    active=set()
    seen=set()
    reasons=[]
    for row in records:
        try:
            key=row["security_id"]
            if not isinstance(key,str) or not key.strip():
                raise ValueError("invalid identity")
            begin=_aware(row["effective_from"])
            end=_aware(row["effective_to"]) if row.get("effective_to") else None
            known=_aware(row["available_at"])
            if end is not None and end<=begin:
                raise ValueError("invalid interval")
            if known>cutoff or not begin<=cutoff or (end is not None and cutoff>=end):
                continue
            if key in seen:
                reasons.append("overlapping_membership:"+key)
            seen.add(key)
            if row.get("evidence_reviewed") is not True or row.get("status") not in ("listed","suspended"):
                reasons.append("membership_unreviewed:"+key)
                continue
            active.add(key)
        except (KeyError,TypeError,ValueError,AttributeError):
            reasons.append("malformed_membership")
    missing=sorted(set(expected)-active)
    unexpected=sorted(active-set(expected))
    return {"missing_ids":missing,"unexpected_ids":unexpected,"reasons":reasons,
            "coverage":len(active & set(expected))/len(expected) if expected else None,
            "research_membership_aligned":bool(expected) and not (missing or unexpected or reasons),
            "survivorship_bias_eliminated":False,"production_eligible":False}
