"""Steps 90-91: deterministic raw evidence package and source-coverage gates."""
from __future__ import annotations
import hashlib, json
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse
from app.p4_26_primary_evidence import validate_primary_notice_archive
from app.p4_27_identity_action_admission import reconcile_corporate_action_assertions, resolve_effective_dated_identities

_ALLOWED_HOSTS = {
 "nepalstock.com.np","www.nepalstock.com","cdsc.com.np","www.cdsc.com.np",
 "sharesansar.com","www.sharesansar.com","chukul.com","www.chukul.com",
 "sharehubnepal.com","www.sharehubnepal.com","punji.com.np","www.punji.com.np",
 "merolagani.com","www.merolagani.com","nepsealpha.com","www.nepsealpha.com",
 "chartnepali.com","www.chartnepali.com","bullhouse.com.np","www.bullhouse.com.np"
}
def _aware(value: object, field: str) -> datetime:
 if not isinstance(value,str): raise ValueError(f"{field}_missing_or_invalid")
 try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
 except ValueError as exc: raise ValueError(f"{field}_invalid") from exc
 if parsed.tzinfo is None or parsed.utcoffset() is None: raise ValueError(f"{field}_must_be_timezone_aware")
 return parsed
def _safe_path(root: Path, relative: str) -> Path:
 p=PurePosixPath(relative)
 if p.is_absolute() or not p.parts or any(x in {"",".",".."} for x in p.parts): raise ValueError("unsafe_evidence_archive_path")
 base=root.resolve(); resolved=(root/Path(*p.parts)).resolve()
 if resolved!=base and base not in resolved.parents: raise ValueError("evidence_archive_path_escapes_root")
 return resolved

def verify_raw_evidence_archive(*, artifacts: list[dict[str,Any]], archive_root: str|Path, decision_cutoff: str, required_artifact_ids: list[str]) -> dict[str,Any]:
 cutoff=_aware(decision_cutoff,"decision_cutoff"); root=Path(archive_root); accepted={}; errors=[]
 for i,row in enumerate(artifacts):
  aid=str(row.get("artifact_id","")).strip()
  try:
   if not aid: raise ValueError("artifact_id_missing")
   if aid in accepted: raise ValueError("duplicate_artifact_id")
   url=str(row.get("source_url","")).strip(); parsed=urlparse(url)
   if parsed.scheme!="https" or parsed.hostname not in _ALLOWED_HOSTS: raise ValueError("source_url_host_not_allowlisted")
   publisher=str(row.get("publisher_id","")).strip(); tier=str(row.get("source_tier","")).strip()
   if not publisher or tier not in {"primary_nepse_or_cdsc","independent_secondary"}: raise ValueError("publisher_or_source_tier_invalid")
   retrieved=_aware(row.get("retrieved_at"),"retrieved_at"); available=_aware(row.get("available_at"),"available_at")
   if retrieved>cutoff or available>cutoff: raise ValueError("artifact_after_decision_cutoff")
   if available>retrieved: raise ValueError("artifact_available_after_retrieval")
   relative=str(row.get("archive_path","")).strip(); raw=_safe_path(root,relative).read_bytes()
   if not raw: raise ValueError("empty_raw_evidence_artifact")
   digest=hashlib.sha256(raw).hexdigest(); expected=str(row.get("sha256","")).lower()
   if len(expected)!=64 or any(c not in "0123456789abcdef" for c in expected) or digest!=expected: raise ValueError("raw_artifact_sha256_mismatch")
   media=str(row.get("media_type","")).strip().lower()
   if not media or "/" not in media: raise ValueError("artifact_media_type_invalid")
   events=sorted({str(x).strip() for x in row.get("event_ids",[]) if str(x).strip()})
   if not events: raise ValueError("artifact_event_coverage_missing")
   accepted[aid]={"artifact_id":aid,"source_url":url,"publisher_id":publisher,"source_tier":tier,"archive_path":relative,"sha256":digest,"bytes":len(raw),"media_type":media,"event_ids":events,"retrieved_at":retrieved.isoformat(),"available_at":available.isoformat()}
  except (ValueError,OSError) as exc: errors.append({"index":i,"artifact_id":aid,"reason":str(exc)})
 missing=sorted(set(required_artifact_ids)-set(accepted))
 if missing: errors.append({"reason":"required_raw_artifacts_missing","artifact_ids":missing})
 ordered=[accepted[k] for k in sorted(accepted)]
 return {"status":"RAW_EVIDENCE_ARCHIVE_VERIFIED" if not errors else "RAW_EVIDENCE_ARCHIVE_BLOCKED","artifact_count":len(accepted),"artifacts":ordered,"missing_artifact_ids":missing,"errors":errors,"manifest_sha256":hashlib.sha256(json.dumps(ordered,sort_keys=True,separators=(",",":")).encode()).hexdigest()}

def run_historical_evidence_package(*, package: dict[str,Any], archive_root: str|Path, decision_cutoff: str) -> dict[str,Any]:
 cutoff=_aware(decision_cutoff,"decision_cutoff")
 try:
  created=_aware(package.get("created_at"),"package_created_at")
  if created>cutoff: raise ValueError("package_created_after_decision_cutoff")
  if package.get("schema_version")!="1.0": raise ValueError("unsupported_evidence_package_schema")
  pid=str(package.get("package_id","")).strip()
  if not pid: raise ValueError("package_id_missing")
 except ValueError as exc:
  return {"status":"EVIDENCE_PACKAGE_BLOCKED","package_id":package.get("package_id"),"errors":[{"reason":str(exc)}],"historical_admission_allowed":False}
 archive=verify_raw_evidence_archive(artifacts=package.get("artifacts",[]),archive_root=archive_root,decision_cutoff=decision_cutoff,required_artifact_ids=package.get("required_artifact_ids",[]))
 idx={x["artifact_id"]:x for x in archive["artifacts"]}; ref_errors=[]
 for kind,records in (("identity",package.get("identity_records",[])),("corporate_action",package.get("corporate_action_records",[]))):
  for i,row in enumerate(records):
   evidence=idx.get(str(row.get("artifact_id","")).strip())
   if not evidence: ref_errors.append({"kind":kind,"index":i,"reason":"linked_raw_artifact_not_verified"}); continue
   if str(row.get("evidence_sha256","")).lower()!=evidence["sha256"]: ref_errors.append({"kind":kind,"index":i,"reason":"record_hash_differs_from_raw_artifact"})
   if str(row.get("publisher_id","")).strip()!=evidence["publisher_id"]: ref_errors.append({"kind":kind,"index":i,"reason":"record_publisher_differs_from_raw_artifact"})
   if row.get("event_id") and row["event_id"] not in evidence["event_ids"]: ref_errors.append({"kind":kind,"index":i,"reason":"raw_artifact_does_not_cover_linked_event"})
 primary=validate_primary_notice_archive(entries=package.get("primary_notice_entries",[]),archive_root=archive_root,decision_cutoff=decision_cutoff,required_event_ids=package.get("required_primary_event_ids",[]))
 identity=resolve_effective_dated_identities(records=package.get("identity_records",[]),required_symbols=package.get("required_identity_symbols",[]),archive_report=primary,decision_cutoff=decision_cutoff)
 actions=reconcile_corporate_action_assertions(records=package.get("corporate_action_records",[]),decision_cutoff=decision_cutoff)
 required=set(package.get("required_action_ids",[])); covered={str(x.get("action_id","")).strip() for x in package.get("corporate_action_records",[]) if str(x.get("action_id","")).strip()}
 missing=sorted(required-covered); coverage=[]
 for aid in sorted(required):
  rows=[x for x in package.get("corporate_action_records",[]) if x.get("action_id")==aid]
  if len({str(x.get("publisher_id","")).strip() for x in rows})<2: coverage.append({"action_id":aid,"reason":"two_distinct_publishers_missing"})
  if not any(x.get("source_tier")=="primary_nepse_or_cdsc" for x in rows): coverage.append({"action_id":aid,"reason":"primary_source_missing"})
 if missing: coverage.append({"reason":"required_action_events_missing","action_ids":missing})
 errors=archive["errors"]+ref_errors+primary["errors"]+identity["errors"]+actions["errors"]+coverage
 ready=not errors and archive["status"]=="RAW_EVIDENCE_ARCHIVE_VERIFIED"
 return {"status":"EVIDENCE_PACKAGE_REVIEW_READY" if ready else "EVIDENCE_PACKAGE_BLOCKED","package_id":pid,"decision_cutoff":cutoff.isoformat(),"raw_archive":archive,"primary_notice_archive":primary,"identity_resolution":identity,"corporate_action_reconciliation":actions,"missing_required_action_ids":missing,"source_coverage_errors":coverage,"errors":errors,"historical_admission_allowed":False,"price_adjustment_admission_allowed":False,"note":"Review-ready evidence is not dataset admission; independent completeness, universe, adjustment-policy and replay gates remain mandatory."}
