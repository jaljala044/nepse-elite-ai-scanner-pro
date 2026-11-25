#!/usr/bin/env python3
"""Verify that source-manifest raw objects exist locally and match SHA-256."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_source_evidence_inventory(manifest_paths: list[str | Path], raw_root: str | Path) -> dict[str, Any]:
    root = Path(raw_root).resolve()
    seen = set()
    checked = []
    errors = []
    for manifest_path in manifest_paths:
        with Path(manifest_path).open(encoding="utf-8") as stream:
            for line_no, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    source_id = str(row["source_id"]).strip()
                    relative_path = str(row["path"]).strip()
                    expected_hash = str(row["sha256"]).lower()
                    local_path = Path(row.get("local_path") or (root / relative_path)).resolve()
                    if not source_id or not relative_path or len(expected_hash) != 64:
                        raise ValueError("source_id, path and 64-character sha256 are required")
                    key = (source_id, relative_path)
                    if key in seen:
                        raise ValueError(f"duplicate manifest object {source_id}:{relative_path}")
                    seen.add(key)
                    if not local_path.is_relative_to(root):
                        raise ValueError("local_path escapes raw_root")
                    if not local_path.is_file():
                        errors.append({"source_id":source_id,"path":relative_path,
                                       "local_path":str(local_path),"status":"missing_raw_object"})
                        continue
                    actual_hash = _sha256(local_path)
                    status = "verified" if actual_hash == expected_hash else "sha256_mismatch"
                    item = {"source_id":source_id,"path":relative_path,
                            "local_path":str(local_path),"expected_sha256":expected_hash,
                            "actual_sha256":actual_hash,"byte_count":local_path.stat().st_size,
                            "status":status}
                    checked.append(item)
                    if status != "verified":
                        errors.append(item)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    errors.append({"manifest":str(manifest_path),"line":line_no,
                                   "status":"invalid_manifest_row","error":str(exc)})
    return {
        "manifest_object_count": len(seen),
        "verified_raw_object_count": sum(row["status"] == "verified" for row in checked),
        "missing_or_mismatched_count": len(errors),
        "checked_objects": checked,
        "errors": errors,
        "status": "passed" if seen and not errors else "failed",
        "canonical_promotion_allowed": False,
        "policy": "raw_bytes_must_exist_and_match_pinned_sha256_no_auto_repair",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="append", required=True, type=Path)
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/reports/source-evidence-inventory.json"))
    args = parser.parse_args()
    report = audit_source_evidence_inventory(args.manifest, args.raw_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "manifest_object_count","verified_raw_object_count","missing_or_mismatched_count",
        "status","canonical_promotion_allowed")}, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
