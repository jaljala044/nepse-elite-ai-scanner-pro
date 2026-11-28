"""Step 99: BENH earliest chart/floorsheet evidence reconciliation."""
from __future__ import annotations
from datetime import date
from typing import Any

def _date(value: str) -> date:
    return date.fromisoformat(value)

def reconcile_benh_first_trade(*, chart_records: list[dict[str,Any]],
                               floorsheet_records: list[dict[str,Any]],
                               floorsheet_coverage_start: str | None,
                               floorsheet_coverage_end: str | None,
                               floorsheet_coverage_verified: bool = False,
                               official_listing_date: str | None = None) -> dict[str,Any]:
    chart_dates=sorted({_date(r["session_date"]) for r in chart_records if r.get("symbol")=="BENH" and r.get("session_date")})
    floor_dates=sorted({_date(r["session_date"]) for r in floorsheet_records if r.get("symbol")=="BENH" and r.get("session_date") and int(r.get("trade_count",0))>0})
    errors=[]
    if not chart_dates: errors.append("no_benh_chart_history")
    if not floor_dates: errors.append("no_benh_floorsheet_trades")
    chart_first=chart_dates[0].isoformat() if chart_dates else None
    floor_first=floor_dates[0].isoformat() if floor_dates else None
    coverage_start=_date(floorsheet_coverage_start) if floorsheet_coverage_start else None
    coverage_end=_date(floorsheet_coverage_end) if floorsheet_coverage_end else None
    bounds_valid=bool(coverage_start and coverage_end and floor_dates and coverage_start<=floor_dates[0] and coverage_end>=floor_dates[-1])
    floor_complete=bool(bounds_valid and floorsheet_coverage_verified)
    corroborated=bool(chart_first and floor_first and chart_first==floor_first)
    listing=_date(official_listing_date) if official_listing_date else None
    first_trade=_date(floor_first) if floor_first else None
    if listing and first_trade and first_trade<listing: errors.append("first_trade_precedes_official_listing_date")
    if not floor_complete: errors.append("floorsheet_archive_completeness_not_established")
    if chart_first and floor_first and chart_first!=floor_first: errors.append("chart_and_floorsheet_first_dates_disagree")
    if listing and first_trade and first_trade<listing: status="BLOCKED"
    elif corroborated and floor_complete: status="FIRST_TRADE_CORROBORATED"
    elif floor_first and floor_complete and not chart_first: status="FLOORSHEET_FIRST_TRADE_CANDIDATE"
    elif chart_first or floor_first: status="PARTIAL_EVIDENCE"
    else: status="NO_EVIDENCE"
    return {"symbol":"BENH","status":status,"chart_first_session":chart_first,
      "floorsheet_first_trade_session":floor_first,"official_listing_date":official_listing_date,
      "chart_and_floorsheet_agree":corroborated,"floorsheet_coverage_start":floorsheet_coverage_start,
      "floorsheet_coverage_end":floorsheet_coverage_end,"floorsheet_coverage_bounds_valid":bounds_valid,
      "floorsheet_coverage_complete":floor_complete,"floorsheet_coverage_verified":floorsheet_coverage_verified,
      "errors":errors,"listing_date_verified":False,
      "first_trade_date_verified":status=="FIRST_TRADE_CORROBORATED",
      "price_history_research_eligible":bool(chart_dates or floor_dates),
      "identity_or_listing_admission_allowed":False}
