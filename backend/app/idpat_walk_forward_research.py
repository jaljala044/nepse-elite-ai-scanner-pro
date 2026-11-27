"""Fixed-rule descriptive evaluation; not executable backtesting."""
from .idpat_outcome_research import evaluate_events
from .idpat_experimental_research import research_events

def walk_forward(rows,assessment_time,train_size=80,test_size=40,horizon=5):
    if any(type(x) is not int for x in (train_size,test_size,horizon)) or horizon<1 or train_size<21+horizon or test_size<21+horizon: raise ValueError("invalid_window")
    research_events(rows,assessment_time)
    folds=[]
    for end in range(train_size,len(rows)-horizon-test_size+1,test_size+horizon):
        train=rows[end-train_size:end]
        test=rows[end+horizon:end+horizon+test_size]
        folds.append(dict(train=evaluate_events(train,train[-1]["available_at"],horizon),
            test=evaluate_events(test,assessment_time,horizon),train_end=train[-1]["observed_at"],test_start=test[0]["observed_at"]))
    return dict(folds=folds,fold_count=len(folds),production_eligible=False,
        limitations=["Fixed rules, no fitting, costs, settlement or executable fills."])
