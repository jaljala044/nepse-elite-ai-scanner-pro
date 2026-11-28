"""Qualify a bounded historical evidence panel across datasets and lifecycle checks."""
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Iterable, Mapping
from zoneinfo import ZoneInfo

_CORE = {"official_market_calendar","official_security_master","official_corporate_actions","cdsc_first_trade"}


def qualify_historical_evidence_panel(*, cohort_symbols: Iterable[str], expected_sessions: Iterable[str],
        ohlcv_ingestion_reports: Iterable[Mapping[str, object]],
        evidence_ingestion_reports: Mapping[str, Mapping[str, object]],
        corporate_action_coverage_attestation: Mapping[str, object],
        decision_cutoff: str) -> dict:
    symbols={str(s).strip().upper() for s in cohort_symbols if str(s).strip()}
    session_list=list(expected_sessions); sessions=set(session_list)
    errors=[]; warnings=[]; coverage={}
    try:
        if not isinstance(decision_cutoff, str):
            raise ValueError("decision_cutoff_must_be_timezone_aware")
        cutoff = datetime.fromisoformat(decision_cutoff.replace("Z", "+00:00"))
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("decision_cutoff_must_be_timezone_aware")
        cutoff_day_text = decision_cutoff[:10]
        cutoff_day = date.fromisoformat(cutoff_day_text)
        if cutoff_day.isoformat() != cutoff_day_text:
            raise ValueError("decision_cutoff_date_must_be_canonical")
        cutoff_local_day = cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date()
        if not symbols or not sessions or len(sessions)!=len(session_list): raise ValueError
        for day in sessions:
            if not isinstance(day, str) or date.fromisoformat(day).isoformat()!=day: raise ValueError
        future_sessions = sorted(day for day in sessions if date.fromisoformat(day) > cutoff_local_day)
        if future_sessions:
            return {"status":"BLOCKED","errors":[{"reason":"expected_session_after_decision_cutoff","sessions":future_sessions}],"backtest_admission_allowed":False,"production_enabled":False}
    except (ValueError,TypeError):
        return {"status":"BLOCKED","errors":[{"reason":"cohort_or_session_window_invalid"}],"backtest_admission_allowed":False,"production_enabled":False}
    bars={}
    for report in ohlcv_ingestion_reports:
        if report.get("status")!="INGESTED" or report.get("all_rows_accepted") is not True:
            errors.append({"reason":"ohlcv_ingestion_report_not_fully_accepted"}); continue
        for row in report.get("rows",[]):
            symbol=str(row.get("symbol","")).upper(); day=str(row.get("session_date",""))
            if symbol not in symbols or day not in sessions:
                errors.append({"symbol":symbol or None,"session_date":day or None,"reason":"ohlcv_outside_requested_cohort_window"}); continue
            key=(symbol,day)
            if key in bars: errors.append({"symbol":symbol,"session_date":day,"reason":"duplicate_ohlcv_symbol_session"})
            else: bars[key]=row
    missing_bars=[{"symbol":s,"session_date":d} for s in sorted(symbols) for d in sorted(sessions) if (s,d) not in bars]
    coverage["ohlcv"]={"expected_symbol_sessions":len(symbols)*len(sessions),"accepted_symbol_sessions":len(bars),"missing":missing_bars}
    if missing_bars: errors.append({"reason":"ohlcv_symbol_session_coverage_incomplete","missing_count":len(missing_bars)})
    for kind in sorted(_CORE):
        report=evidence_ingestion_reports.get(kind)
        if not isinstance(report,Mapping) or report.get("status")!="INGESTED" or report.get("all_rows_accepted") is not True:
            errors.append({"dataset_kind":kind,"reason":"required_evidence_dataset_not_fully_ingested"})
            coverage[kind]={"status":"MISSING_OR_BLOCKED","row_count":0}
        else: coverage[kind]={"status":"INGESTED","row_count":len(report.get("rows",[]))}
    calendar=evidence_ingestion_reports.get("official_market_calendar",{})
    if isinstance(calendar,Mapping) and calendar.get("status")=="INGESTED":
        opened={str(r.get("session_date")) for r in calendar.get("rows",[]) if r.get("is_open") is True}
        absent=sorted(sessions-opened)
        if absent: errors.append({"reason":"expected_session_not_confirmed_open_by_calendar","sessions":absent})
        coverage["calendar_open_session_coverage"]={"expected":len(sessions),"confirmed_open":len(sessions&opened),"missing":absent}
    master=evidence_ingestion_reports.get("official_security_master",{})
    if isinstance(master,Mapping) and master.get("status")=="INGESTED":
        identities={}
        for row in master.get("rows",[]):
            symbol=str(row.get("symbol","")).upper()
            if symbol in symbols: identities.setdefault(symbol,[]).append(row)
        missing=sorted(symbols-set(identities))
        if missing: errors.append({"reason":"permanent_security_identity_missing","symbols":missing})
        for symbol,records in identities.items():
            if len(records)!=1: errors.append({"symbol":symbol,"reason":"security_master_identity_not_unique"})
            for row in records:
                try:
                    start=date.fromisoformat(str(row["effective_from"]))
                    end=date.fromisoformat(str(row["effective_to"])) if row.get("effective_to") else None
                    for day in sessions:
                        d=date.fromisoformat(day)
                        if d<start or (end and d>end): errors.append({"symbol":symbol,"session_date":day,"reason":"session_outside_security_lifecycle"})
                except (KeyError,ValueError,TypeError):
                    errors.append({"symbol":symbol,"reason":"security_lifecycle_dates_invalid"})
        coverage["security_identity"]={"cohort_symbols":len(symbols),"symbols_with_identity":len(identities),"missing":missing}
    att=corporate_action_coverage_attestation
    action_ok=(isinstance(att,Mapping) and att.get("complete_for_requested_window") is True and att.get("human_reviewed") is True and bool(str(att.get("reviewer_id","")).strip()) and bool(str(att.get("evidence_reference","")).strip()))
    if not action_ok: errors.append({"reason":"corporate_action_window_coverage_attestation_missing"})
    else:
        try:
            start=date.fromisoformat(str(att["window_start"])); end=date.fromisoformat(str(att["window_end"]))
            if start>min(date.fromisoformat(s) for s in sessions) or end<max(date.fromisoformat(s) for s in sessions):
                errors.append({"reason":"corporate_action_attestation_does_not_cover_panel_window"})
        except (ValueError,KeyError,TypeError): errors.append({"reason":"corporate_action_attestation_window_invalid"})
    actions=evidence_ingestion_reports.get("official_corporate_actions",{})
    if isinstance(actions,Mapping) and actions.get("status")=="INGESTED":
        invalid=sorted({str(r.get("symbol","")).upper() for r in actions.get("rows",[]) if str(r.get("symbol","")).upper() not in symbols})
        if invalid: errors.append({"reason":"corporate_action_rows_outside_cohort","symbols":invalid})
        coverage["corporate_actions"]={"row_count":len(actions.get("rows",[])),"window_attestation_valid":action_ok}
    first=evidence_ingestion_reports.get("cdsc_first_trade",{})
    if isinstance(first,Mapping) and first.get("status")=="INGESTED":
        first_by_symbol={str(r.get("symbol","")).upper():r for r in first.get("rows",[])}
        missing=sorted(symbols-set(first_by_symbol))
        if missing: errors.append({"reason":"cdsc_first_trade_evidence_missing","symbols":missing})
        for symbol,row in first_by_symbol.items():
            if symbol not in symbols: errors.append({"symbol":symbol,"reason":"first_trade_record_outside_cohort"}); continue
            try:
                first_day=date.fromisoformat(str(row["first_trade_date"]))
                first_bar=min(date.fromisoformat(d) for s,d in bars if s==symbol)
                if first_day!=first_bar: errors.append({"symbol":symbol,"cdsc_first_trade_date":str(first_day),"first_ohlcv_date":str(first_bar),"reason":"first_trade_vs_first_ohlcv_mismatch"})
            except (KeyError,ValueError,TypeError): errors.append({"symbol":symbol,"reason":"first_trade_date_unverifiable"})
        coverage["cdsc_first_trade"]={"cohort_symbols":len(symbols),"verified_rows":len(first_by_symbol),"missing":missing}
    for kind in ("official_floorsheet","official_sector_indices","official_broker_trade_summary"):
        report=evidence_ingestion_reports.get(kind)
        if isinstance(report,Mapping) and report.get("status")=="INGESTED": coverage[kind]={"status":"INGESTED","row_count":len(report.get("rows",[]))}
        else:
            coverage[kind]={"status":"NOT_SUPPLIED","row_count":0}
            warnings.append({"dataset_kind":kind,"reason":"supplemental_dataset_not_supplied"})
    ready=not errors
    return {"status":"PANEL_EVIDENCE_QUALIFIED_FOR_HUMAN_REVIEW" if ready else "BLOCKED",
        "cohort_symbol_count":len(symbols),"expected_session_count":len(sessions),"coverage":coverage,
        "errors":errors,"warnings":warnings,"human_review_required":True,"research_replay_admission_required":True,
        "publisher_authenticity_proven":False,"exchange_wide_completeness_proven":False,
        "backtest_admission_allowed":False,"canonical_promotion_allowed":False,"production_enabled":False,
        "limitations":["Qualification is limited to the explicit cohort and requested session window.",
          "Calendar and corporate-action completeness remain operator-attested and require independent review.",
          "CDSC first-trade dates are compared with first supplied OHLCV observations, not treated as proof of exchange-wide listing completeness.",
          "Supplemental floorsheet, sector and broker datasets improve scanner evidence but do not substitute for core panel gates."]}
