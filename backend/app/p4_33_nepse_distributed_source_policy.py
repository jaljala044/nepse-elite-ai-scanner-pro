"""Step 98: trust policy for NEPSE-derived data distributed by established Nepal platforms.

Provider classification is configurable. Trust in a distribution channel does not waive
record-level validation, timestamps, identity checks, coverage checks or cross-checks.
"""
from __future__ import annotations
from typing import Any

DEFAULT_PROVIDERS={
 "sharehub":{"display_name":"ShareHub Nepal","claimed_lineage":"NEPSE-derived distribution","enabled":True},
 "chukul":{"display_name":"Chukul","claimed_lineage":"NEPSE-derived distribution","enabled":True},
 "sharesansar":{"display_name":"ShareSansar","claimed_lineage":"NEPSE-derived distribution","enabled":True},
 "punji":{"display_name":"Punji","claimed_lineage":"NEPSE-derived distribution","enabled":True},
 "merolagani":{"display_name":"Merolagani","claimed_lineage":"NEPSE-derived distribution","enabled":True},
 "nepsealpha":{"display_name":"NepseAlpha","claimed_lineage":"NEPSE-derived distribution","enabled":True},
 "chartnepali":{"display_name":"ChartNepali","claimed_lineage":"NEPSE-derived distribution","enabled":True},
 "bullhouse":{"display_name":"Bullhouse Investment","claimed_lineage":"NEPSE-derived distribution","enabled":True},
}

def classify_source_record(*, provider_id: str, captured_at: str, published_at: str | None,
                           raw_sha256: str, symbol: str, session_date: str,
                           fields_present: list[str], expected_fields: list[str],
                           independent_check_status: str = "pending",
                           provider_registry: dict[str,dict[str,Any]] | None = None) -> dict[str,Any]:
    registry=provider_registry or DEFAULT_PROVIDERS
    provider=registry.get(provider_id.lower())
    errors=[]
    if not provider or not provider.get("enabled"): errors.append("provider_not_registered_or_disabled")
    if not captured_at: errors.append("capture_timestamp_missing")
    if not symbol.strip(): errors.append("symbol_missing")
    if not session_date.strip(): errors.append("session_date_missing")
    if len(raw_sha256)!=64 or any(c not in "0123456789abcdefABCDEF" for c in raw_sha256):
        errors.append("raw_sha256_invalid")
    missing=sorted(set(expected_fields)-set(fields_present))
    if missing: errors.append("required_fields_missing")
    if published_at and published_at>captured_at: errors.append("published_after_capture")
    if errors:
        status="QUARANTINED"
    elif independent_check_status=="match":
        status="CORROBORATED"
    elif independent_check_status=="conflict":
        status="CONFLICT_REVIEW"
    else:
        status="TRUSTED_DISTRIBUTION_PENDING_CROSSCHECK"
    return {"provider_id":provider_id.lower(),"provider_name":provider.get("display_name") if provider else None,
      "source_lineage":provider.get("claimed_lineage") if provider else "unknown",
      "status":status,"errors":errors,"missing_fields":missing,
      "independent_check_status":independent_check_status,
      "primary_exchange_origin_independently_proven":False,
      "raw_sha256":raw_sha256,"symbol":symbol,"session_date":session_date,
      "eligible_for_research":status in {"CORROBORATED","TRUSTED_DISTRIBUTION_PENDING_CROSSCHECK"},
      "eligible_for_production_signal":status=="CORROBORATED"}
