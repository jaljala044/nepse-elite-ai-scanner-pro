"""Raw archive diagnostics, never point-in-time certification."""
import csv,io,hashlib
from datetime import date
from decimal import Decimal

def audit_archive(text):
    rows=list(csv.DictReader(io.StringIO(text)))
    seen=set(); duplicates=[]; invalid=[]
    for r in rows:
        d=r.get("Date")
        try:
            date.fromisoformat(d)
            o,h,l,c,v=(Decimal(r[k]) for k in ("Open","High","Low","Close","Volume"))
            if not all(x.is_finite() for x in (o,h,l,c,v)) or not 0<l<=min(o,c)<=max(o,c)<=h or v<0: raise ValueError()
        except (ValueError,TypeError,KeyError,ArithmeticError):
            invalid.append(d); continue
        if d in seen: duplicates.append(d)
        seen.add(d)
    return dict(rows=len(rows),unique_valid_dates=len(seen),duplicates=duplicates,invalid=invalid,sha256=hashlib.sha256(text.encode()).hexdigest(),backtest_eligible=False,reason="point_in_time_calendar_and_price_basis_evidence_required")
