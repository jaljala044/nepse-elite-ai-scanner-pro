"""Dated published equity brokerage caps; not a complete verified cost schedule."""
from datetime import date
from decimal import Decimal

BOUNDS = (50000,500000,2000000,10000000)
SCHEDULES = (
    (date(2020,12,27),("0.0040","0.0037","0.0034","0.0030","0.0027")),
    (date(2024,5,14),("0.0036","0.0033","0.0031","0.0027","0.0024")),
)
EVIDENCE = (
    "https://www.sharesansar.com/newsdetail/board-decides-to-decrease-the-commission-rate-2020-12-25",
    "https://www.sharesansar.com/newsdetail/sebon-to-enact-revised-commission-rates-for-stockbrokers-implementation-begins-today-2024-05-14",
    "https://www.investopaper.com/news/stock-broker-commission-nepal/",
)
def brokerage_cap(day, notional):
    day = date.fromisoformat(str(day))
    n = Decimal(str(notional))
    if not n.is_finite() or n <= 0:
        raise ValueError("positive finite notional required")
    applicable = [s for s in SCHEDULES if s[0]<=day]
    if not applicable or day>date(2026,11,26):
        return {"status":"unavailable","rate":None}
    start,rates = applicable[-1]
    index = sum(n>b for b in BOUNDS)
    return {"status":"published_third_party_reference","effective_from":str(start),
            "rate":rates[index],"source_urls":list(EVIDENCE),
            "production_eligible":False}

def resident_tax_reference(sale_date, holding_days):
    day=date.fromisoformat(str(sale_date))
    if isinstance(holding_days,bool) or not isinstance(holding_days,int) or holding_days<0:
        raise ValueError("invalid holding period")
    # Exact start dates of earlier regimes require additional verification.
    if date(2026,9,22)<=day<=date(2026,11,26):
        return {"status":"published_third_party_reference","rate":"0.0375" if holding_days>365 else "0.05",
                "source_urls":["https://www.sharesansar.com/newsdetail/capital-gains-tax-rates-reduced-decision-published-in-gazette-2026-09-22"],
                "production_eligible":False}
    return {"status":"effective_date_not_certified","rate":None}
