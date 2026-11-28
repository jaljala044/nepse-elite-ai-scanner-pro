"""Steps 160-169: validate daily market-wide ShareSansar CSV archive rows."""
from __future__ import annotations
import csv
from datetime import date
from io import StringIO
from typing import Any

REQUIRED=("Symbol","Open","High","Low","Close","Vol","Turnover","Trans.")

def _number(value: Any) -> float:
    if value is None: raise ValueError("missing_numeric")
    return float(str(value).replace(",","").strip())

def parse_daily_market_csv(text: str, *, session_date: str, source_url: str, retrieved_at: str) -> dict[str, Any]:
    """Parse one complete daily CSV response. No network or filesystem side effects."""
    try: session=date.fromisoformat(session_date).isoformat()
    except (TypeError,ValueError): return {"status":"REJECTED","errors":["invalid_session_date"],"records":[],"production_admission_allowed":False}
    errors=[]
    reader=csv.DictReader(StringIO(text))
    headers=reader.fieldnames or []
    missing=[x for x in REQUIRED if x not in headers]
    if missing: return {"status":"REJECTED","errors":["missing_columns:"+",".join(missing)],"records":[],"production_admission_allowed":False}
    records=[]; seen=set(); row_errors=[]
    for line,row in enumerate(reader,start=2):
        symbol=(row.get("Symbol") or "").strip().upper()
        if not symbol:
            row_errors.append(f"line_{line}_missing_symbol"); continue
        if symbol in seen:
            row_errors.append(f"line_{line}_duplicate_symbol_{symbol}"); continue
        seen.add(symbol)
        try:
            o,h,l,c=(_number(row[k]) for k in ("Open","High","Low","Close"))
            vol=_number(row["Vol"]); turnover=_number(row["Turnover"]); transactions=_number(row["Trans."])
            if min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c) or l>h:
                raise ValueError("invalid_ohlc")
            if min(vol,turnover,transactions)<0: raise ValueError("negative_activity")
            records.append({
                "symbol":symbol,"session_date":session,"open":o,"high":h,"low":l,"close":c,
                "volume":vol,"turnover":turnover,"transactions":transactions,
                "provider":"sharesansar_scraper_public_archive","source_url":source_url,
                "retrieved_at":retrieved_at,"source_class":"UNOFFICIAL_THIRD_PARTY_ARCHIVE",
                "scope":"DAILY_MARKET_WIDE_CSV","quality":"RESEARCH_ONLY",
                "production_admission_allowed":False
            })
        except (TypeError,ValueError):
            row_errors.append(f"line_{line}_invalid_market_row_{symbol}")
    errors.extend(row_errors)
    return {"status":"REJECTED" if errors else "RESEARCH_ONLY_VALIDATED","errors":errors,
            "records":records,"row_count":len(records),"unique_symbols":len(seen),
            "session_date":session,"file_scope":"MARKET_WIDE_DAILY_SNAPSHOT",
            "production_admission_allowed":False}

def find_symbol_record(parsed: dict[str,Any], symbol: str) -> dict[str,Any]:
    matches=[r for r in parsed.get("records",[]) if r["symbol"]==symbol.strip().upper()]
    if len(matches)==1: return {"status":"FOUND","record":matches[0]}
    if not matches: return {"status":"NOT_PRESENT_IN_ARCHIVE_FILE","record":None}
    return {"status":"AMBIGUOUS_DUPLICATE","record":None}
