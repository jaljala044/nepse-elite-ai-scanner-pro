"""Validate this adjudicated conflict set; not a canonical/training release."""
import json
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/evidence/acquired"
ledger = json.loads((BASE / "ohlcv-conflict-ledger-2026-11-25.json").read_text())
doc = json.loads((BASE / "ohlcv-project-resolution-2026-11-26.json").read_text())
def require(condition, message):
    if not condition:
        raise ValueError(message)
def key(row):
    return row["symbol"], row["date"]
expected = {key(x): x for x in ledger["conflicts"]}
rows = doc["records"]
require(len(rows) == len(expected) == 8 and {key(x) for x in rows} == set(expected), "Conflict coverage mismatch")
providers = {"NEPSE", "ShareHub", "Chukul", "ShareSansar", "NepseAlpha"}
require(set(doc["acceptance_policy"]["approved_providers"]) == providers, "Provider policy mismatch")
for row in rows:
    k = key(row)
    provider = row["approved_provider"]
    require(provider in providers and row["project_evidence_accepted"] is True, f"{k}: approval missing")
    values = tuple(map(Decimal, row["ohlcv"]))
    o,h,l,c,v = values
    require(all(x.is_finite() for x in values) and 0 < l <= min(o,c) <= max(o,c) <= h and v > 0 and v == v.to_integral_value(), f"{k}: invalid OHLCV")
    original = expected[k]
    require(values in [tuple(map(Decimal, map(str, original[s]["ohlcv"]))) for s in ("source_a","source_b")], f"{k}: value not in original dispute")
    source = row["source"]
    if provider == "NEPSE":
        raw = json.loads((ROOT / source["response_path"]).read_text())
        records = raw if isinstance(raw,list) else raw["content"]
        matches = [x for x in records if (x["symbol"],x["businessDate"]) == k]
        require(len(matches)==1, f"{k}: missing raw primary row")
        observed = tuple(Decimal(str(matches[0][f])) for f in ("openPrice","highPrice","lowPrice","closePrice","totalTradedQuantity"))
        require(values == observed, f"{k}: raw mismatch")
    elif provider == "ShareHub":
        audit = doc["uploaded_evidence_reverification"]["checks"]
        require(audit["arithmetic_errors"] == 0 and audit["page_count_or_endpoint_id_errors"] == 0 and audit["distinct_contracts"] == audit["contract_rows"] == 2793 and audit["july_final_15_minute_close_matches"] == 5, "ShareHub audit incomplete")
        require(values == tuple(map(Decimal, source["secondary_archive"]["observed_ohlcv"])) and source["audit_git_blob_oid"], f"{k}: corroboration missing")
    else:
        raise ValueError(f"{k}: new provider evidence adapter required")
    require(row["canonical_promotion_allowed"] is False, "Unexpected canonical promotion")
require(doc["summary"]["training_allowed"] is False and doc["summary"]["canonical_promotion_allowed"] is False, "Unexpected promotion")
print("PASS: eight adjudicated OHLCV records meet approved-provider project evidence policy; training remains blocked.")
