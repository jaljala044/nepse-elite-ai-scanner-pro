"""Execute a capture only from a previously approved, reviewed source contract."""
from __future__ import annotations
from typing import Callable, Mapping
from app.historical_pilot_capture_runner import capture_registered_source_pages


def capture_approved_historical_source(*, source_contract_report: Mapping[str, object], fetch_page: Callable[[str], Mapping[str, object]], captured_at: str, decision_cutoff: str) -> dict:
    """Pass only the reviewed capture specification to the bounded transport runner."""
    if not isinstance(source_contract_report, Mapping) or source_contract_report.get("status") != "SOURCE_CONTRACT_APPROVED_FOR_CAPTURE" or source_contract_report.get("capture_allowed") is not True:
        return {"status":"CAPTURE_BLOCKED","errors":[{"reason":"source_contract_not_approved"}],"manifest":None,"payloads":{},"capture_complete":False,"backtest_admission_allowed":False,"production_enabled":False}
    spec = source_contract_report.get("capture_spec")
    if not isinstance(spec, Mapping):
        return {"status":"CAPTURE_BLOCKED","errors":[{"reason":"approved_capture_spec_missing"}],"manifest":None,"payloads":{},"capture_complete":False,"backtest_admission_allowed":False,"production_enabled":False}
    max_pages = spec.get("max_pages")
    if isinstance(max_pages,bool) or not isinstance(max_pages,int) or not 1 <= max_pages <= 1000:
        return {"status":"CAPTURE_BLOCKED","errors":[{"reason":"approved_max_pages_invalid"}],"manifest":None,"payloads":{},"capture_complete":False,"backtest_admission_allowed":False,"production_enabled":False}
    result = capture_registered_source_pages(source_spec=spec,fetch_page=fetch_page,captured_at=captured_at,decision_cutoff=decision_cutoff,max_pages=max_pages)
    result["source_contract_status"] = source_contract_report.get("status")
    result["source_contract_approval_reference"] = spec.get("authority_evidence_ref")
    result["source_contract_dataset_kind"] = spec.get("dataset_kind")
    result["network_transport_injected_by_operator"] = True
    result["backtest_admission_allowed"] = False
    result["production_enabled"] = False
    return result
