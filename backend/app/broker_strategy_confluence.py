"""Unified descriptive evidence envelope; does not combine scores or issue actions."""
from .idpat_v3 import evaluate_idpat_v3

def unified_research(*,symbol,as_of,mode,ohlcv,smc_result,ict_result,idpat_result,broker_result):
    if mode not in ("swing","positional"): raise ValueError("unsupported mode")
    base={"status":"insufficient_evidence","symbol":symbol,"as_of":as_of,"mode":mode,
          "score":None,"action":"NO TRADE","production_eligible":False,"signals_enabled":False,
          "source_authentication_performed":False}
    # No independently versioned ICT engine exists in this repository yet.
    # Never accept caller-supplied labels as proof that ICT rules were executed.
    if ict_result.get("engine_id") != "nepse_ict_research" or ict_result.get("engine_version") is None or ict_result.get("evidence_sha256") is None:
        return dict(base,reason="ict_engine_not_implemented_or_unverified")
    for name,result in (("smc",smc_result),("ict",ict_result),("idpat",idpat_result),("broker",broker_result)):
        if not isinstance(result,dict): return dict(base,reason=name+"_result_missing")
        if result.get("as_of")!=as_of: return dict(base,reason=name+"_as_of_mismatch")
    idpat=evaluate_idpat_v3(ohlcv,eligible=False)
    if idpat["status"] not in ("eligibility_unverified","specification_unverified","insufficient_data","data_quality_failed"):
        return dict(base,reason="unexpected_idpat_state")
    checks={
        "smc":smc_result.get("status") in ("research_only","experimental_only","incomplete"),
        "ict":ict_result.get("status") in ("research_only","experimental_only","incomplete") and bool(ict_result.get("engine_version")) and len(str(ict_result.get("evidence_sha256")))==64,
        "idpat":idpat_result.get("status") in ("research_features_ready","specification_unverified","insufficient_data"),
        "broker":broker_result.get("status")=="insufficient_evidence" and broker_result.get("signals_enabled") is False
    }
    if not all(checks.values()):
        return dict(base,reason="component_not_research_eligible",component_checks=checks)
    return dict(base,status="research_only",reason="component_evidence_not_independently_validated",
        component_checks=checks,idpat_specification_verified=False,
        limitations=["Component outputs are reported independently; scores are not added.",
                     "ICT input must carry an independently versioned research result.",
                     "IDPAT V3.0 proprietary thresholds remain unverified.",
                     "Broker confirmation remains withheld pending historical identity certification."])
