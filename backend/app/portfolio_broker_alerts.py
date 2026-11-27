"""Broker turnover imbalance is not beneficial ownership or manipulation evidence."""
from decimal import Decimal
from .corporate_action_risk import _amount
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available

WINDOWS = ("1D","1W","1M","3M","6M","1Y","2Y")

def review_holding_broker_flow(*, symbol, records, assessment_time, price_evidence=None):
    now = _time(assessment_time)
    windows = {}
    for record in records:
        _available(record, now, "broker_flow")
        if record["symbol"] != symbol:
            raise ValueError("broker_symbol_mismatch")
        window = record["window"]
        if window not in WINDOWS or window in windows:
            raise ValueError("invalid_or_duplicate_window")
        start, end = _time(record["start_at"]), _time(record["end_at"])
        if not start < end <= _time(record["available_at"]) <= now:
            raise ValueError("invalid_broker_window_dates")
        if record.get("complete") is not True:
            continue
        if window in windows:
            raise ValueError("duplicate_window")
        # Selected cohort, not all market brokers (aggregate buys equal sells).
        cohort = record["broker_numbers"]
        if not isinstance(cohort,list) or not cohort or len(set(cohort)) != len(cohort):
            raise ValueError("invalid_broker_cohort")
        buy = _amount(record["buy_turnover"],"buy_turnover")
        sell = _amount(record["sell_turnover"],"sell_turnover")
        total = buy+sell
        if not total:
            continue
        imbalance = (buy-sell)/total
        windows[window] = dict(imbalance=float(imbalance),cohort=sorted(cohort),
            source_id=record["source_id"],end_at=end.isoformat(),
            direction="SELL_DOMINANT" if imbalance <= Decimal("-.2") else
                      "BUY_DOMINANT" if imbalance >= Decimal(".2") else "NEUTRAL")
    short = [windows.get(w) for w in ("1D","1W","1M")]
    comparable = all(short) and len({tuple(x["cohort"]) for x in short}) == 1 and len({x["end_at"] for x in short}) == 1
    persistent_sell = bool(comparable and all(x["direction"]=="SELL_DOMINANT" for x in short))
    persistent_buy = bool(comparable and all(x["direction"]=="BUY_DOMINANT" for x in short))
    breakdown = False
    if price_evidence is not None:
        _available(price_evidence, now, "price_evidence")
        if price_evidence["symbol"] != symbol:
            raise ValueError("price_symbol_mismatch")
        close = _amount(price_evidence["close"],"close")
        support = _amount(price_evidence["support"],"support")
        if not close or not support:
            raise ValueError("invalid_price_evidence")
        breakdown = close < support
    action = ("EXIT_REVIEW" if persistent_sell and breakdown else
              "DISTRIBUTION_RISK_REVIEW" if persistent_sell else
              "ACCUMULATION_WATCH" if persistent_buy else "WAIT" if comparable else "UNKNOWN")
    return dict(symbol=symbol,action=action,windows={w:windows.get(w) for w in WINDOWS},
                comparable_short_windows=bool(comparable),price_breakdown=breakdown if price_evidence else None,
                execution_eligible=False,profit_booking_status="NOT_ASSESSED",
                limitations=["Caller-attested cohort turnover; not ownership or manipulation evidence.",
                             "Overlapping windows are not independent confirmations.",
                             "Threshold of 20% is a research rule, not calibrated probability.",
                             "Window duration, cohort selection and freshness require independent validation."])
