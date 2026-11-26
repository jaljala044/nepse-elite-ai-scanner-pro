"""Server-side reviewed profile repository; never trusts client supplied controls."""
import json
from datetime import date
from pathlib import Path
from .actual_volume_profile import actual_volume_profile
from .floorsheet_contract import FloorsheetContract

ROOT=Path(__file__).resolve().parents[2]/"data"/"reference"/"reviewed_volume_profiles"

def load_profile(symbol, start, end, *, root=None):
    base={"status":"unavailable","symbol":symbol,"levels":[],"production_score":None,
          "start":str(start),"end":str(end)}
    if start>end or (end-start).days>366:
        return dict(base,reason="invalid_date_range")
    root=ROOT if root is None else root
    if not symbol.isascii() or not symbol.isalnum() or len(symbol)>20:
        return dict(base,reason="invalid_symbol")
    path=root/symbol/f"{start}_{end}.json"
    try:
        with path.open(encoding="utf-8") as f:
            manifest=json.load(f)
        if manifest.get("schema_version")!=1 or manifest.get("reviewed") is not True or manifest.get("symbol")!=symbol or manifest.get("start")!=str(start) or manifest.get("end")!=str(end) or not manifest.get("calendar_evidence_id"):
            return dict(base,reason="unreviewed_manifest")
        days=[date.fromisoformat(d) for d in manifest["sessions"]]
        if not days or any(d<start or d>end for d in days):
            return dict(base,reason="invalid_session_scope")
        contracts=[FloorsheetContract.from_mapping(r,source_id=r["source_id"],
            payload_sha256=r["source_payload_sha256"],row_number=r["source_row_number"])
            for r in manifest["contracts"]]
        result=actual_volume_profile(symbol,contracts,sessions=days,controls=manifest["controls"],eligible=True)
        return dict(result,start=str(start),end=str(end),calendar_evidence_id=manifest["calendar_evidence_id"])
    except FileNotFoundError:
        return dict(base,reason="reviewed_profile_manifest_missing")
    except (OSError,ValueError,TypeError,KeyError,AttributeError,ArithmeticError):
        return dict(base,reason="invalid_reviewed_manifest")
