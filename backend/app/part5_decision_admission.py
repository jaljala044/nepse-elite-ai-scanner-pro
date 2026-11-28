"""Research-only per-decision admission and label maturity checks."""
from datetime import datetime
from collections.abc import Mapping
from .historical_segment_eligibility import evaluate_historical_segment
from .point_in_time import _aware

def admit_decision(*, segment_inputs, decision_time, features, minimum_features=1):
    """Caller evidence is not independently authenticated; never promotes data."""
    reasons = []
    if type(minimum_features) is not int or minimum_features < 1:
        raise ValueError("positive minimum_features required")
    cutoff = _aware(decision_time)
    segment = evaluate_historical_segment(**{**segment_inputs, "decision_cutoff": decision_time})
    reasons.extend(segment["reasons"])
    seen = set()
    for row in features:
        try:
            key = row["record_id"]
            if not isinstance(key, str) or not key.strip() or key in seen:
                raise ValueError("invalid or duplicate feature ID")
            seen.add(key)
            event = _aware(row["event_at"])
            available = _aware(row["available_at"])
            if not event <= available <= cutoff:
                reasons.append("feature_time_order:" + key)
            if row.get("evidence_reviewed") is not True:
                reasons.append("feature_evidence_unreviewed:" + key)
        except (KeyError, TypeError, ValueError, AttributeError):
            reasons.append("malformed_feature")
    if len(seen) < minimum_features:
        reasons.append("insufficient_features")
    return {"exploratory_eligible": not reasons, "reasons": reasons,
            "approved_backtest_eligible": False, "production_eligible": False}

def mature_training_rows(rows, *, fit_cutoff, first_test_decision):
    """Exclude overlapping or not-yet-known labels; never fit a model here."""
    fit, test = _aware(fit_cutoff), _aware(first_test_decision)
    if fit >= test:
        raise ValueError("fit cutoff must precede first test decision")
    included, excluded = [], []
    seen = set()
    for row in rows:
        key = row.get("record_id")
        if not isinstance(key, str) or not key.strip() or key in seen:
            raise ValueError("unique record_id required")
        seen.add(key)
        try:
            decision, feature, end, available = (_aware(row[k]) for k in
                ("decision_at", "feature_available_at", "label_end_at", "label_available_at"))
            valid = feature <= decision < end <= available <= fit and end < test
        except (KeyError, TypeError, ValueError, AttributeError):
            valid = False
        (included if valid else excluded).append(key)
    return {"included_ids": included, "excluded_ids": excluded,
            "status": "research_only" if included else "insufficient_sample",
            "production_eligible": False}
