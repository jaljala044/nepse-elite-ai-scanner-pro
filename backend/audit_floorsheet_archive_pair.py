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
from pathlib import Path

from app.floorsheet_archive_pair_audit import audit_floorsheet_archive_pair
from app.floorsheet_source_profiles import (
    samir_merolagani_capture_mapping,
    socrateai_floorsheet_mapping,
    urek_floorsheet_mapping,
    review_samir_merolagani_headers,
    review_socrateai_floorsheet_headers,
    review_urek_floorsheet_headers,
)


PROFILES = {
    "samir": (samir_merolagani_capture_mapping, review_samir_merolagani_headers),
    "socrateai": (socrateai_floorsheet_mapping, review_socrateai_floorsheet_headers),
    "urek": (urek_floorsheet_mapping, review_urek_floorsheet_headers),
}


def load_profile_payload(path: Path, profile_name: str):
    payload = path.read_bytes()
    if not payload:
        raise ValueError(f"{path} is empty")
    try:
        header = next(csv.reader(payload.decode("utf-8-sig").splitlines()))
    except (UnicodeDecodeError, StopIteration, csv.Error) as exc:
        raise ValueError(f"cannot read CSV header from {path}") from exc
    mapping_factory, review_headers = PROFILES[profile_name]
    review = review_headers(header)
    if not review.valid:
        raise ValueError(
            f"{profile_name} header mismatch: missing={review.missing_headers}, "
            f"unexpected={review.unexpected_headers}, duplicates={review.duplicate_headers}"
        )
    return payload, mapping_factory()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for side in ("left", "right"):
        parser.add_argument(f"--{side}-file", required=True, type=Path)
        parser.add_argument(f"--{side}-source-id", required=True)
        parser.add_argument(f"--{side}-profile", required=True, choices=sorted(PROFILES))
        parser.add_argument(f"--{side}-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    left_payload, left_mapping = load_profile_payload(args.left_file, args.left_profile)
    right_payload, right_mapping = load_profile_payload(args.right_file, args.right_profile)
    report = audit_floorsheet_archive_pair(
        left_payload, right_payload,
        left_source_id=args.left_source_id, right_source_id=args.right_source_id,
        left_expected_sha256=args.left_sha256, right_expected_sha256=args.right_sha256,
        left_mapping=left_mapping, right_mapping=right_mapping,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "audit_status": report["audit_status"],
        "left_sha256": report["left_file"]["sha256"],
        "right_sha256": report["right_file"]["sha256"],
        "output": str(args.output),
        "canonical_promotion_allowed": report["canonical_promotion_allowed"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
