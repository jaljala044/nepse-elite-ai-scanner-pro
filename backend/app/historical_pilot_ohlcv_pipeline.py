"""Dataset-specific bridge from validated raw capture to normalized OHLCV rows."""
from __future__ import annotations
from typing import Mapping
from app.historical_pilot_capture_package import accept_historical_capture_package
from app.historical_pilot_ingest import ingest_captured_ohlcv_csv


def ingest_accepted_historical_ohlcv_capture(*, source_contract_report: Mapping[str, object], capture_result: Mapping[str, object], payloads: Mapping[str, bytes], column_map: Mapping[str, str], decision_cutoff: str) -> dict:
    """Accept and ingest an approved EOD OHLCV capture without schema inference."""
    spec = source_contract_report.get("capture_spec") if isinstance(source_contract_report,Mapping) else None
    if not isinstance(spec,Mapping) or spec.get("dataset_kind") != "official_eod_ohlcv":
        return {"status":"INGESTION_BLOCKED","errors":[{"reason":"dataset_kind_not_official_eod_ohlcv"}],"rows":[],"row_count":0,"backtest_admission_allowed":False,"production_enabled":False}
    package = accept_historical_capture_package(source_contract_report=source_contract_report,capture_result=capture_result,payloads=payloads,decision_cutoff=decision_cutoff)
    if package.get("status") != "CAPTURE_PACKAGE_ACCEPTED_FOR_PANEL_INGESTION":
        return {"status":"INGESTION_BLOCKED","errors":[{"reason":"capture_package_not_accepted","details":package.get("errors",[])}],"rows":[],"row_count":0,"capture_package":package,"backtest_admission_allowed":False,"production_enabled":False}
    report = package.get("validation_report")
    manifest = capture_result.get("manifest") if isinstance(capture_result,Mapping) else None
    if not isinstance(report,Mapping) or not isinstance(manifest,Mapping):
        return {"status":"INGESTION_BLOCKED","errors":[{"reason":"validated_manifest_or_report_missing"}],"rows":[],"row_count":0,"capture_package":package,"backtest_admission_allowed":False,"production_enabled":False}
    ingestion = ingest_captured_ohlcv_csv(capture_report=report,manifest=manifest,payloads=payloads,column_map=column_map,decision_cutoff=decision_cutoff)
    return {
        "status":"INGESTED" if ingestion.get("status") == "INGESTED" and ingestion.get("all_rows_accepted") is True else "INGESTION_BLOCKED",
        **ingestion,
        "source_id":report.get("source_id"),"publisher_id":report.get("publisher_id"),
        "capture_id":report.get("capture_id"),"capture_manifest_sha256":report.get("manifest_sha256"),
        "capture_package_status":package.get("status"),"dataset_kind":"official_eod_ohlcv",
        "explicit_column_map_used":True,"schema_inference_used":False,
        "backtest_admission_allowed":False,"canonical_promotion_allowed":False,"production_enabled":False,
    }
