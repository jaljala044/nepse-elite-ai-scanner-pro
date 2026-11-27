"""Chronological expanding-window folds with embargoed label-overlap boundaries."""
from __future__ import annotations
from datetime import date

DEFAULT_EMBARGO_SESSIONS = 120

def _dates(values):
    if not isinstance(values,list) or len(values)<20: raise ValueError("at_least_20_session_dates_required")
    parsed=[]
    for value in values:
        try: d=date.fromisoformat(value)
        except (TypeError,ValueError): raise ValueError("invalid_session_date") from None
        if parsed and d<=parsed[-1]: raise ValueError("session_dates_must_be_unique_and_chronological")
        parsed.append(d)
    return parsed

def build_walk_forward_folds(*, session_dates, minimum_train_sessions=500,
    validation_sessions=60, out_of_sample_sessions=60, step_sessions=60,
    embargo_sessions=DEFAULT_EMBARGO_SESSIONS, maximum_folds=5):
    """Plan expanding train/validation/test windows; returned indices are half-open.

    Embargo bars are omitted between each partition so an outcome label cannot
    cross from one partition into the next. All strategies must reuse these folds.
    """
    dates=_dates(session_dates)
    for name,value in (("minimum_train_sessions",minimum_train_sessions),
        ("validation_sessions",validation_sessions),("out_of_sample_sessions",out_of_sample_sessions),
        ("step_sessions",step_sessions),("maximum_folds",maximum_folds)):
        if isinstance(value,bool) or not isinstance(value,int) or value<1: raise ValueError(name+"_must_be_positive_integer")
    if isinstance(embargo_sessions,bool) or not isinstance(embargo_sessions,int) or embargo_sessions<0:
        raise ValueError("embargo_sessions_must_be_non_negative_integer")
    folds=[]
    # Start each fold with an expanding training history; subsequent test windows advance by step_sessions.
    train_end=minimum_train_sessions
    while len(folds)<maximum_folds:
        val_start=train_end+embargo_sessions
        val_end=val_start+validation_sessions
        test_start=val_end+embargo_sessions
        test_end=test_start+out_of_sample_sessions
        if test_end>len(dates): break
        folds.append({"fold":len(folds)+1,
            "train":{"start_index":0,"end_index":train_end,"start_date":dates[0].isoformat(),"end_date":dates[train_end-1].isoformat(),"session_count":train_end},
            "embargo_train_validation":{"start_index":train_end,"end_index":val_start,"session_count":embargo_sessions},
            "validation":{"start_index":val_start,"end_index":val_end,"start_date":dates[val_start].isoformat(),"end_date":dates[val_end-1].isoformat(),"session_count":validation_sessions},
            "embargo_validation_test":{"start_index":val_end,"end_index":test_start,"session_count":embargo_sessions},
            "out_of_sample":{"start_index":test_start,"end_index":test_end,"start_date":dates[test_start].isoformat(),"end_date":dates[test_end-1].isoformat(),"session_count":out_of_sample_sessions}})
        train_end += step_sessions
    return {"schema_version":"nepse-walk-forward-1.0.0","folds":folds,
        "fold_count":len(folds),"session_count":len(dates),
        "embargo_sessions":embargo_sessions,"maximum_label_horizon_sessions":embargo_sessions,
        "partition_policy":"expanding_train_then_validation_then_forward_out_of_sample_with_embargo",
        "common_fold_policy":"reuse exact fold date/index boundaries for all six strategies and four horizons",
        "untouched_holdout_policy":"the final out_of_sample block must not be used for feature or threshold tuning",
        "status":"ready_for_research" if folds else "insufficient_history",
        "limitations":["The planner does not create signals, labels, or guarantee that callers respect boundaries.",
            "Embargo must be at least the maximum outcome-label horizon; 120 is the default for this project.",
            "Repeated out-of-sample folds are walk-forward evaluation; reserve a final untouched holdout if model selection is extensive."],
        "production_enabled":False}
