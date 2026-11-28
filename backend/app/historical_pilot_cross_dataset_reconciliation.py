"""Cross-dataset consistency audit for a bounded historical NEPSE cohort."""
from __future__ import annotations
from datetime import date
from typing import Iterable, Mapping

def reconcile_historical_datasets(*, cohort_symbols: Iterable[str], expected_sessions: Iterable[str],
        ohlcv_ingestion_reports: Iterable[Mapping[str, object]],
        evidence_ingestion_reports: Mapping[str, Mapping[str, object]]) -> dict:
    symbols={str(s).strip().upper() for s in cohort_symbols if str(s).strip()}
    sessions={str(s) for s in expected_sessions}
    issues=[]; counts={}; bars={}
    for report in ohlcv_ingestion_reports:
        if report.get("status")!="INGESTED" or report.get("all_rows_accepted") is not True:
            issues.append({"severity":"BLOCKER","dataset":"ohlcv","reason":"ingestion_report_not_accepted"}); continue
        for row in report.get("rows",[]):
            sym=str(row.get("symbol","")).upper(); day=str(row.get("session_date",""))
            if (sym,day) in bars: issues.append({"severity":"BLOCKER","symbol":sym,"session_date":day,"reason":"duplicate_ohlcv_key"})
            bars[(sym,day)]=row
    def rows(kind):
        report=evidence_ingestion_reports.get(kind)
        if not isinstance(report,Mapping) or report.get("status")!="INGESTED" or report.get("all_rows_accepted") is not True:
            issues.append({"severity":"BLOCKER","dataset":kind,"reason":"required_or_supplied_report_not_accepted"}); return []
        return list(report.get("rows",[]))
    calendar=rows("official_market_calendar")
    opened={str(r.get("session_date")) for r in calendar if r.get("is_open") is True}
    closed={str(r.get("session_date")) for r in calendar if r.get("is_open") is False}
    for day in sorted(sessions):
        if day in closed: issues.append({"severity":"BLOCKER","session_date":day,"reason":"ohlcv_expected_on_official_closed_day"})
        elif day not in opened: issues.append({"severity":"WARNING","session_date":day,"reason":"official_open_session_not_confirmed"})
    master=rows("official_security_master"); lifecycle={}
    for r in master:
        sym=str(r.get("symbol","")).upper()
        if sym in symbols: lifecycle.setdefault(sym,[]).append(r)
    for sym in sorted(symbols):
        if len(lifecycle.get(sym,[]))!=1:
            issues.append({"severity":"BLOCKER","symbol":sym,"reason":"security_identity_missing_or_ambiguous"}); continue
        r=lifecycle[sym][0]
        try:
            start=date.fromisoformat(str(r["effective_from"])); end=date.fromisoformat(str(r["effective_to"])) if r.get("effective_to") else None
            for (s,day) in bars:
                if s==sym:
                    d=date.fromisoformat(day)
                    if d<start or (end and d>end): issues.append({"severity":"BLOCKER","symbol":sym,"session_date":day,"reason":"ohlcv_outside_security_lifecycle"})
        except (KeyError,ValueError,TypeError): issues.append({"severity":"BLOCKER","symbol":sym,"reason":"security_lifecycle_unverifiable"})
    actions=rows("official_corporate_actions")
    for r in actions:
        sym=str(r.get("symbol","")).upper()
        if sym not in symbols: issues.append({"severity":"BLOCKER","symbol":sym,"reason":"corporate_action_outside_cohort"})
        try:
            ex=date.fromisoformat(str(r["ex_date"]))
            if ex.isoformat() not in sessions: issues.append({"severity":"WARNING","symbol":sym,"ex_date":ex.isoformat(),"reason":"corporate_action_ex_date_outside_panel_window"})
        except (KeyError,ValueError,TypeError): issues.append({"severity":"BLOCKER","symbol":sym,"reason":"corporate_action_ex_date_unverifiable"})
    first=rows("cdsc_first_trade"); first_by={str(r.get("symbol","")).upper():r for r in first}
    for sym in sorted(symbols):
        if sym not in first_by:
            issues.append({"severity":"BLOCKER","symbol":sym,"reason":"cdsc_first_trade_missing"}); continue
        supplied=[date.fromisoformat(d) for s,d in bars if s==sym]
        try:
            official=date.fromisoformat(str(first_by[sym]["first_trade_date"]))
            if supplied and official!=min(supplied):
                issues.append({"severity":"BLOCKER","symbol":sym,"cdsc_first_trade_date":official.isoformat(),"first_supplied_bar":min(supplied).isoformat(),"reason":"first_trade_vs_first_supplied_bar_mismatch"})
        except (KeyError,ValueError,TypeError): issues.append({"severity":"BLOCKER","symbol":sym,"reason":"cdsc_first_trade_unverifiable"})
    for kind in ("official_floorsheet","official_sector_indices","official_broker_trade_summary"):
        report=evidence_ingestion_reports.get(kind)
        if not isinstance(report,Mapping) or report.get("status")!="INGESTED":
            counts[kind]={"status":"NOT_SUPPLIED","rows":0}; continue
        data=list(report.get("rows",[])); counts[kind]={"status":"INGESTED","rows":len(data)}
        for r in data:
            day=str(r.get("session_date",""))
            if kind=="official_floorsheet":
                sym=str(r.get("symbol","")).upper()
                if sym not in symbols or day not in sessions: issues.append({"severity":"WARNING","dataset":kind,"symbol":sym,"session_date":day,"reason":"trade_outside_panel_scope"})
                if day in closed: issues.append({"severity":"BLOCKER","dataset":kind,"symbol":sym,"session_date":day,"reason":"floorsheet_trade_on_official_closed_day"})
            elif kind=="official_broker_trade_summary":
                sym=str(r.get("symbol","")).upper()
                if (sym,day) not in bars: issues.append({"severity":"WARNING","dataset":kind,"symbol":sym,"session_date":day,"reason":"broker_summary_without_matching_ohlcv"})
            elif day not in sessions: issues.append({"severity":"WARNING","dataset":kind,"session_date":day,"reason":"sector_observation_outside_panel_window"})
    counts["ohlcv"]={"status":"INGESTED","rows":len(bars),"symbol_sessions":len(bars)}
    blockers=sum(x["severity"]=="BLOCKER" for x in issues); warnings=sum(x["severity"]=="WARNING" for x in issues)
    return {"status":"REVIEW_REQUIRED" if issues else "CONSISTENT_FOR_HUMAN_REVIEW",
      "cohort_symbol_count":len(symbols),"expected_session_count":len(sessions),"dataset_counts":counts,
      "issue_count":len(issues),"blocker_count":blockers,"warning_count":warnings,"issues":issues,
      "human_review_required":True,"backtest_admission_allowed":False,"canonical_promotion_allowed":False,
      "production_enabled":False,"publisher_authenticity_proven":False,"exchange_wide_completeness_proven":False,
      "limitations":["Checks are bounded to supplied cohort, sessions and accepted reports.",
      "Absent corporate-action rows do not prove that no corporate action occurred.",
      "Broker IDs identify execution channels, not beneficial owners; anomalies do not prove manipulation."]}
