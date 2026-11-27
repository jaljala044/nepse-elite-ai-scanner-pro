"""Research-only broker pattern memory from supplied daily observations."""
from collections import defaultdict
from decimal import Decimal
from .corporate_action_risk import _amount
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available, _day

def replay_broker_patterns(*, records, sessions, assessment_time):
    now = _time(assessment_time)
    days = [_day(x,"session") for x in sessions]
    if not days or days != sorted(set(days)) or days[-1] > now.date():
        raise ValueError("invalid_sessions")
    index = {d:i for i,d in enumerate(days)}
    groups = defaultdict(dict)
    for r in records:
        _available(r,now,"broker_observation")
        day = _day(r["date"],"observation_date")
        if day not in index or _time(r["available_at"]).date() < day:
            raise ValueError("invalid_observation_date")
        cohort = r["broker_numbers"]
        if not isinstance(cohort,list) or not cohort or any(type(b) is not int or b<=0 for b in cohort) or len(set(cohort))!=len(cohort):
            raise ValueError("invalid_cohort")
        key = (r["symbol"],tuple(sorted(cohort)))
        if day in groups[key]:
            raise ValueError("duplicate_observation")
        groups[key][day] = r
    histories = []
    for (symbol,cohort), observations in sorted(groups.items()):
        streak = 0
        prior = None
        events = []
        for day in days:
            r = observations.get(day)
            if r is None or r.get("complete") is not True:
                streak,prior = 0,None
                continue
            buy,sell = _amount(r["buy_turnover"],"buy"),_amount(r["sell_turnover"],"sell")
            close = _amount(r["close"],"close")
            if not buy+sell or not close:
                streak,prior = 0,None
                continue
            imbalance = (buy-sell)/(buy+sell)
            direction = 1 if imbalance>=Decimal(".2") else -1 if imbalance<=Decimal("-.2") else 0
            old = streak
            streak = old+direction if old*direction>0 else direction
            flags = []
            if abs(streak)==3:
                flags.append("ACCUMULATION_PATTERN" if streak>0 else "DISTRIBUTION_PATTERN")
            if old*direction<0:
                flags.append("FLOW_REVERSAL")
            if prior is not None and close>prior and direction<0:
                flags.append("SELLING_INTO_STRENGTH")
            events.append(dict(date=day.isoformat(),available_at=r["available_at"],source_id=r["source_id"],
                               imbalance=float(imbalance),streak=streak,flags=flags))
            prior=close
        histories.append(dict(symbol=symbol,broker_numbers=list(cohort),observations=events,
                              coverage=len(events)/len(days),latest_streak=streak))
    return dict(classification="retrospective_broker_pattern_replay",histories=histories,
                execution_eligible=False,limitations=[
                    "Not persistent storage or point-in-time historical signal generation.",
                    "Missing sessions reset streaks; supplied calendar and observations require independent verification.",
                    "20% imbalance and three-session streak are provisional research rules.",
                    "Broker cohort activity does not establish ownership or manipulation."])
