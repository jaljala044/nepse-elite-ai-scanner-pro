"""CLI for reproducible review-only comparison of two pinned floorsheet CSVs.

Example (from repository root):
python backend/audit_floorsheet_archive_pair.py \
  --left-file /path/left.csv --left-source-id left@commit \
  --left-profile samir --left-sha256 <64-hex> \
  --right-file /path/right.csv --right-source-id right@commit \
  --right-profile socrateai --right-sha256 <64-hex> \
  --output /path/report.json

No network access, source download, or canonical promotion is performed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from app.floorsheet_archive_pair_audit import audit_floorsheet_archive_pair
from app.floorsheet_source_profiles import (
    SAMIR_BLOB_SHA1, SAMIR_FLOORSHEET_PATH, SAMIR_PINNED_COMMIT,
    SAMIR_RAW_SHA256, SAMIR_RAW_SIZE_BYTES, SAMIR_REPO_ID,
    SOCRATEAI_BLOB_SHA1, SOCRATEAI_FLOORSHEET_PATH,
    SOCRATEAI_PINNED_COMMIT, SOCRATEAI_RAW_SIZE_BYTES, SOCRATEAI_REPO_ID,
    UREK_FOLDER, UREK_PINNED_REVISION, UREK_REPO_ID,
    samir_merolagani_capture_mapping, socrateai_floorsheet_mapping,
    urek_floorsheet_mapping, review_samir_merolagani_headers,
    review_socrateai_floorsheet_headers, review_urek_floorsheet_headers,
)


PROFILES = {
    "samir": {
        "mapping": samir_merolagani_capture_mapping,
        "review": review_samir_merolagani_headers,
        "repository": SAMIR_REPO_ID,
        "revision": SAMIR_PINNED_COMMIT,
        "path": SAMIR_FLOORSHEET_PATH,
        "expected_blob_sha1": SAMIR_BLOB_SHA1,
        "expected_raw_sha256": SAMIR_RAW_SHA256,
        "expected_size_bytes": SAMIR_RAW_SIZE_BYTES,
    },
    "socrateai": {
        "mapping": socrateai_floorsheet_mapping,
        "review": review_socrateai_floorsheet_headers,
        "repository": SOCRATEAI_REPO_ID,
        "revision": SOCRATEAI_PINNED_COMMIT,
        "path": SOCRATEAI_FLOORSHEET_PATH,
        "expected_blob_sha1": SOCRATEAI_BLOB_SHA1,
        "expected_raw_sha256": None,
        "expected_size_bytes": SOCRATEAI_RAW_SIZE_BYTES,
    },
    "urek": {
        "mapping": urek_floorsheet_mapping,
        "review": review_urek_floorsheet_headers,
        "repository": UREK_REPO_ID,
        "revision": UREK_PINNED_REVISION,
        "path": UREK_FOLDER,
        "expected_blob_sha1": None,
        "expected_raw_sha256": None,
        "expected_size_bytes": None,
    },
}


def load_profile_payload(path: Path, profile_name: str):
    payload = path.read_bytes()
    if not payload:
        raise ValueError(f"{path} is empty")
    try:
        header = next(csv.reader(payload.decode("utf-8-sig").splitlines()))
    except (UnicodeDecodeError, StopIteration, csv.Error) as exc:
        raise ValueError(f"cannot read CSV header from {path}") from exc
    profile = PROFILES[profile_name]
    review = profile["review"](header)
    if not review.valid:
        raise ValueError(
            f"{profile_name} header mismatch: missing={review.missing_headers}, "
            f"unexpected={review.unexpected_headers}, duplicates={review.duplicate_headers}"
        )
    return payload, profile["mapping"](), review


def source_manifest(profile_name, source_id, path, expected_sha256, payload, review):
    profile = PROFILES[profile_name]
    return {
        "source_id": source_id,
        "profile": profile_name,
        "repository": profile["repository"],
        "pinned_revision": profile["revision"],
        "profile_path": profile["path"],
        "expected_git_blob_sha1": profile["expected_blob_sha1"],
        "profile_expected_raw_sha256": profile["expected_raw_sha256"],
        "profile_expected_size_bytes": profile["expected_size_bytes"],
        "local_path": str(path),
        "local_size_bytes": len(payload),
        "local_sha256": hashlib.sha256(payload).hexdigest(),
        "caller_expected_sha256": expected_sha256,
        "header_review": asdict(review),
        "profile_evidence_status": review.evidence_status,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for side in ("left", "right"):
        parser.add_argument(f"--{side}-file", required=True, type=Path)
        parser.add_argument(f"--{side}-source-id", required=True)
        parser.add_argument(f"--{side}-profile", required=True, choices=sorted(PROFILES))
        parser.add_argument(f"--{side}-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    left_payload, left_mapping, left_review = load_profile_payload(args.left_file, args.left_profile)
    right_payload, right_mapping, right_review = load_profile_payload(args.right_file, args.right_profile)
    audit = audit_floorsheet_archive_pair(
        left_payload, right_payload,
        left_source_id=args.left_source_id, right_source_id=args.right_source_id,
        left_expected_sha256=args.left_sha256, right_expected_sha256=args.right_sha256,
        left_mapping=left_mapping, right_mapping=right_mapping,
    )
    report = {
        "schema_version": "1.1",
        "left_source_manifest": source_manifest(
            args.left_profile, args.left_source_id, args.left_file,
            args.left_sha256, left_payload, left_review,
        ),
        "right_source_manifest": source_manifest(
            args.right_profile, args.right_source_id, args.right_file,
            args.right_sha256, right_payload, right_review,
        ),
        "audit": audit,
        "audit_status": audit["audit_status"],
        "source_independence_verified": False,
        "source_rights_verified": False,
        "daily_capture_completeness_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "audit_status": report["audit_status"],
        "left_sha256": report["left_source_manifest"]["local_sha256"],
        "right_sha256": report["right_source_manifest"]["local_sha256"],
        "output": str(args.output),
        "canonical_promotion_allowed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
