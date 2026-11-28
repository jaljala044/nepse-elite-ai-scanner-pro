"""Steps 150-159: import the public ShareSansarScraper compact BENH archive."""
from datetime import date
from typing import Any

ARCHIVE_COLUMNS = ("d", "o", "h", "l", "c", "ltp", "vwap", "vol", "to", "dp")

def parse_public_symbol_history(payload: dict[str, Any], *, source_url: str, retrieved_at: str) -> dict[str, Any]:
    """Normalize a public compact-column history while preserving its unofficial provenance."""
    errors=[]
    if not isinstance(payload, dict) or not payload.get("symbol"):
        return {"status":"REJECTED","errors":["invalid_payload"],"records":[],"production_admission_allowed":False}
    cols=payload.get("cols")
    rows=payload.get("rows")
    if not isinstance(cols,list) or tuple(cols)!=ARCHIVE_COLUMNS:
        errors.append("unexpected_or_reordered_columns")
    if not isinstance(rows,list):
        errors.append("rows_not_list")
        rows=[]
    records=[]
    seen=set()
    for index, raw in enumerate(rows):
        if not isinstance(raw,list) or len(raw)!=len(ARCHIVE_COLUMNS):
            errors.append(f"row_{index}_wrong_width")
            continue
        item=dict(zip(ARCHIVE_COLUMNS,raw))
        try:
            session=date.fromisoformat(item["d"]).isoformat()
            prices={k:float(item[k]) for k in ("o","h","l","c")}
            volume=float(item["vol"])
            turnover=float(item["to"])
            if any(v<=0 for v in prices.values()) or prices["l"]>min(prices["o"],prices["c"]) or prices["h"]<max(prices["o"],prices["c"]) or prices["l"]>prices["h"]:
                raise ValueError("invalid_ohlc")
            if volume<0 or turnover<0:
                raise ValueError("negative_volume_or_turnover")
            if session in seen:
                errors.append(f"duplicate_session_{session}")
                continue
            seen.add(session)
            records.append({
                "symbol":payload["symbol"],"session_date":session,
                "open":prices["o"],"high":prices["h"],"low":prices["l"],"close":prices["c"],
                "ltp":item["ltp"],"vwap":item["vwap"],"volume":volume,"turnover":turnover,
                "change_pct":item["dp"],"provider":"sharesansar_scraper_public_archive",
                "source_url":source_url,"retrieved_at":retrieved_at,
                "source_class":"UNOFFICIAL_THIRD_PARTY_ARCHIVE",
                "scope":"DAILY_EOD_ARCHIVE_CANDIDATE","quality":"RESEARCH_ONLY",
                "production_admission_allowed":False
            })
        except (TypeError,ValueError,KeyError):
            errors.append(f"row_{index}_invalid_values")
    if records and [r["session_date"] for r in records] != sorted(r["session_date"] for r in records):
        errors.append("sessions_not_chronological")
    return {"status":"REJECTED" if errors else "RESEARCH_ONLY_VALIDATED",
            "errors":errors,"records":records,"record_count":len(records),
            "coverage_start":records[0]["session_date"] if records else None,
            "coverage_end":records[-1]["session_date"] if records else None,
            "missing_session_semantics":"ABSENCE_FROM_SYMBOL_HISTORY_IS_NOT_PROOF_OF_ZERO_MARKET_TRADES",
            "production_admission_allowed":False}
