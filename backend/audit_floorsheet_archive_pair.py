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
import re
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


def load_profile_payload(path: Path, profile_name: str, *, expected_git_blob_sha1: str | None = None):
    payload = path.read_bytes()
    if not payload:
        raise ValueError(f"{path} is empty")
    try:
        header = next(csv.reader(payload.decode("utf-8-sig").splitlines()))
    except (UnicodeDecodeError, StopIteration, csv.Error) as exc:
        raise ValueError(f"cannot read CSV header from {path}") from exc
    profile = PROFILES[profile_name]
    if expected_git_blob_sha1 is not None:
        if not isinstance(expected_git_blob_sha1, str) or not re.fullmatch(r"[0-9a-f]{40}", expected_git_blob_sha1):
            raise ValueError("expected Git blob SHA-1 must be 40 lowercase hexadecimal characters")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        actual_blob_sha1 = hashlib.sha1(git_blob).hexdigest()
        if actual_blob_sha1 != expected_git_blob_sha1:
            raise ValueError(f"{profile_name} Git blob SHA-1 does not match supplied date-specific pin")
        # The explicit date-specific pin binds this payload. Keep the profile's
        # header schema/mapping, but do not apply its old single-day size/hash.
    else:
        if profile["expected_size_bytes"] is not None and len(payload) != profile["expected_size_bytes"]:
            raise ValueError(
                f"{profile_name} byte-size mismatch: expected "
                f"{profile['expected_size_bytes']}, observed {len(payload)}"
            )
        if profile["expected_raw_sha256"] is not None:
            raw_sha256 = hashlib.sha256(payload).hexdigest()
            if raw_sha256 != profile["expected_raw_sha256"]:
                raise ValueError(f"{profile_name} raw SHA-256 does not match pinned profile")
        if profile["expected_blob_sha1"] is not None:
            git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
            if hashlib.sha1(git_blob).hexdigest() != profile["expected_blob_sha1"]:
                raise ValueError(f"{profile_name} Git blob SHA-1 does not match pinned profile")
    review = profile["review"](header)
    if not review.valid:
        raise ValueError(
            f"{profile_name} header mismatch: missing={review.missing_headers}, "
            f"unexpected={review.unexpected_headers}, duplicates={review.duplicate_headers}"
        )
    return payload, profile["mapping"](), review


def source_manifest(profile_name, source_id, path, expected_sha256, payload, review,
                    *, expected_git_blob_sha1: str | None = None):
    profile = PROFILES[profile_name]
    dynamic_blob_pin = expected_git_blob_sha1 is not None
    if dynamic_blob_pin and (
        not isinstance(source_id, str)
        or not source_id.endswith("@blob:" + expected_git_blob_sha1)
    ):
        raise ValueError("source_id does not match date-specific Git blob pin")
    return {
        "source_id": source_id,
        "profile": profile_name,
        "repository": profile["repository"],
        "pinned_revision": None if dynamic_blob_pin else profile["revision"],
        "profile_path": None if dynamic_blob_pin else profile["path"],
        "expected_git_blob_sha1": expected_git_blob_sha1 or profile["expected_blob_sha1"],
        "profile_expected_raw_sha256": None if dynamic_blob_pin else profile["expected_raw_sha256"],
        "profile_expected_size_bytes": None if dynamic_blob_pin else profile["expected_size_bytes"],
        "payload_pin_mode": "explicit_date_specific_git_blob_sha1" if dynamic_blob_pin else "static_profile_pin",
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
        parser.add_argument(f"--{side}-expected-git-blob-sha1")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    left_payload, left_mapping, left_review = load_profile_payload(
        args.left_file, args.left_profile, expected_git_blob_sha1=args.left_expected_git_blob_sha1
    )
    right_payload, right_mapping, right_review = load_profile_payload(
        args.right_file, args.right_profile, expected_git_blob_sha1=args.right_expected_git_blob_sha1
    )
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
            expected_git_blob_sha1=args.left_expected_git_blob_sha1,
        ),
        "right_source_manifest": source_manifest(
            args.right_profile, args.right_source_id, args.right_file,
            args.right_sha256, right_payload, right_review,
            expected_git_blob_sha1=args.right_expected_git_blob_sha1,
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
