"""Point-in-time historical symbol/session completeness audit for bounded cohorts."""
from __future__ import annotations
from datetime import date
from typing import Iterable, Mapping

def audit_historical_panel_completeness(*, cohort_symbols: Iterable[str], expected_sessions: Iterable[str], ohlcv_ingestion_reports: Iterable[Mapping[str, object]], official_calendar_report: Mapping[str, object], security_master_report: Mapping[str, object], first_trade_report: Mapping[str, object]) -> dict:
    symbols={str(s).strip().upper() for s in cohort_symbols if str(s).strip()}
    sessions=sorted(set(str(x) for x in expected_sessions)); issues=[]; bars=set()
    for report in ohlcv_ingestion_reports:
        if report.get("status")!="INGESTED" or report.get("all_rows_accepted") is not True:
            issues.append({"severity":"BLOCKER","reason":"ohlcv_report_not_fully_accepted"}); continue
        for row in report.get("rows",[]):
            key=(str(row.get("symbol","")).upper(),str(row.get("session_date","")))
            if key in bars: issues.append({"severity":"BLOCKER","symbol":key[0],"session_date":key[1],"reason":"duplicate_symbol_session"})
            bars.add(key)
    def valid(report): return isinstance(report,Mapping) and report.get("status")=="INGESTED" and report.get("all_rows_accepted") is True
    if not valid(official_calendar_report) or not valid(security_master_report) or not valid(first_trade_report):
        return {"status":"BLOCKED","issues":issues+[{"severity":"BLOCKER","reason":"official_calendar_security_master_and_first_trade_reports_required"}],"backtest_admission_allowed":False,"production_enabled":False}
    calendar=official_calendar_report.get("rows",[])
    opened={str(r.get("session_date")) for r in calendar if r.get("is_open") is True}; closed={str(r.get("session_date")) for r in calendar if r.get("is_open") is False}
    if opened & closed: issues.append({"severity":"BLOCKER","reason":"calendar_open_closed_conflict","sessions":sorted(opened&closed)})
    master={}
    for row in security_master_report.get("rows",[]):
        sym=str(row.get("symbol","")).upper()
        if sym in symbols: master.setdefault(sym,[]).append(row)
    first={str(r.get("symbol","")).upper():r for r in first_trade_report.get("rows",[])}
    by_symbol={}; total_expected=0; total_present=0
    for sym in sorted(symbols):
        records=master.get(sym,[])
        if len(records)!=1: issues.append({"severity":"BLOCKER","symbol":sym,"reason":"security_master_identity_missing_or_ambiguous"}); continue
        try:
            start=date.fromisoformat(str(records[0]["effective_from"])); end=date.fromisoformat(str(records[0]["effective_to"])) if records[0].get("effective_to") else None
            first_day=date.fromisoformat(str(first[sym]["first_trade_date"]))
        except (KeyError,ValueError,TypeError):
            issues.append({"severity":"BLOCKER","symbol":sym,"reason":"listing_lifecycle_or_first_trade_unverifiable"}); continue
        if first_day<start: issues.append({"severity":"BLOCKER","symbol":sym,"reason":"cdsc_first_trade_precedes_effective_listing"})
        missing=[]; present=0; eligible=0; excluded=[]
        for day in sessions:
            d=date.fromisoformat(day)
            if day not in opened:
                if day in closed: excluded.append(day)
                else: issues.append({"severity":"WARNING","symbol":sym,"session_date":day,"reason":"calendar_session_status_unknown"})
                continue
            if d<start or (end and d>end) or d<first_day: excluded.append(day); continue
            eligible+=1; total_expected+=1
            if (sym,day) in bars: present+=1; total_present+=1
            else: missing.append(day)
        by_symbol[sym]={"eligible_open_sessions":eligible,"observed_bars":present,"missing_open_sessions":missing,"closed_or_outside_lifecycle_excluded":excluded,"coverage_ratio":present/eligible if eligible else None}
        if missing: issues.append({"severity":"BLOCKER","symbol":sym,"reason":"missing_expected_open_session_bars","sessions":missing})
    outside=sorted([{"symbol":s,"session_date":d} for s,d in bars if s not in symbols or d not in sessions],key=lambda x:(x["symbol"],x["session_date"]))
    if outside: issues.append({"severity":"BLOCKER","reason":"ohlcv_rows_outside_requested_cohort_window","rows":outside})
    ratio=total_present/total_expected if total_expected else None
    return {"status":"COMPLETE_FOR_HUMAN_REVIEW" if not issues else "INCOMPLETE_OR_CONFLICTED","symbol_coverage":by_symbol,"expected_open_symbol_sessions":total_expected,"observed_symbol_sessions":total_present,"overall_coverage_ratio":ratio,"issue_count":len(issues),"blocker_count":sum(x["severity"]=="BLOCKER" for x in issues),"issues":issues,"exchange_wide_completeness_proven":False,"backtest_admission_allowed":False,"canonical_promotion_allowed":False,"production_enabled":False,"limitations":["Completeness is bounded to supplied cohort and explicit official open sessions.","Unknown calendar dates are not assumed open or closed.","No delisted universe beyond supplied security-master records is inferred."]}
