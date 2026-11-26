"""Compare multiple exact pinned overlapping Samir/SocrateAI floorsheet dates.

The pinned manifest below contains Git tree object SHA-1 and byte sizes for
each file at immutable source commits. Raw files are fetched by the workflow;
this script validates bytes, parses, and compares without promoting coverage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.floorsheet_archive_pair_audit import audit_floorsheet_archive_pair
from app.floorsheet_source_profiles import (
    SAMIR_PINNED_COMMIT,
    SAMIR_REPO_ID,
    SOCRATEAI_PINNED_COMMIT,
    SOCRATEAI_REPO_ID,
    samir_merolagani_capture_mapping,
    socrateai_floorsheet_mapping,
    review_samir_merolagani_headers,
    review_socrateai_floorsheet_headers,
)
from audit_floorsheet_archive_pair import load_profile_payload


PINNED_DATES = {
    "2026-11-19": {
        "samir": {"path": "data/floorsheet/floorsheet_2026-11-19.csv", "size": 2752514, "blob_sha1": "43263388769de5b8e8e1801533dc3b41c100de99"},
        "socrateai": {"path": "floorsheet/floorsheet_2026-11-19.csv", "size": 2383640, "blob_sha1": "84c7afbda588fc5fcebc346a954172c43809c616"},
    },
    "2026-11-20": {
        "samir": {"path": "data/floorsheet/floorsheet_2026-11-20.csv", "size": 2695245, "blob_sha1": "d6e6234288aa1f2e4cb8f68b91c70441fcc044b3"},
        "socrateai": {"path": "floorsheet/floorsheet_2026-11-20.csv", "size": 2335392, "blob_sha1": "6f74994849641296e2a16cad22fb555b08955c35"},
    },
    "2026-11-24": {
        "samir": {"path": "data/floorsheet/floorsheet_2026-11-24.csv", "size": 3538179, "blob_sha1": "22eaa891b30aac2fe4cf197053efa014953351c0"},
        "socrateai": {"path": "floorsheet/floorsheet_2026-11-24.csv", "size": 3058892, "blob_sha1": "e7150873219d66a21345df2dfbd78f6c5a4b1152"},
    },
}


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    ).hexdigest()


def verify_pinned_payload(payload: bytes, *, expected_size: int, expected_blob_sha1: str, label: str):
    if not isinstance(payload, bytes) or not payload:
        raise ValueError(f"{label} payload must be non-empty bytes")
    if len(payload) != expected_size:
        raise ValueError(f"{label} byte-size mismatch: expected {expected_size}, got {len(payload)}")
    observed_blob = git_blob_sha1(payload)
    if observed_blob != expected_blob_sha1:
        raise ValueError(f"{label} Git blob SHA-1 mismatch: expected {expected_blob_sha1}, got {observed_blob}")
    return {
        "byte_size": len(payload),
        "git_blob_sha1": observed_blob,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def audit_pinned_archive_window(input_dir: str | Path) -> dict:
    root = Path(input_dir)
    date_reports = {}
    for day, sources in PINNED_DATES.items():
        left_path = root / f"samir-{day}.csv"
        right_path = root / f"socrateai-{day}.csv"
        left_payload = left_path.read_bytes()
        right_payload = right_path.read_bytes()
        left_meta = verify_pinned_payload(
            left_payload, expected_size=sources["samir"]["size"],
            expected_blob_sha1=sources["samir"]["blob_sha1"],
            label=f"Samir {day}",
        )
        right_meta = verify_pinned_payload(
            right_payload, expected_size=sources["socrateai"]["size"],
            expected_blob_sha1=sources["socrateai"]["blob_sha1"],
            label=f"SocrateAI {day}",
        )

        # Header reviews are tied to the exact observed source schemas.
        import csv
        left_header = next(csv.reader(left_payload.decode("utf-8-sig").splitlines()))
        right_header = next(csv.reader(right_payload.decode("utf-8-sig").splitlines()))
        left_review = review_samir_merolagani_headers(left_header)
        right_review = review_socrateai_floorsheet_headers(right_header)
        if not left_review.valid:
            raise ValueError(f"Samir {day} header mismatch: {left_review}")
        if not right_review.valid:
            raise ValueError(f"SocrateAI {day} header mismatch: {right_review}")

        pair = audit_floorsheet_archive_pair(
            left_payload, right_payload,
            left_source_id=f"{SAMIR_REPO_ID}@{SAMIR_PINNED_COMMIT}:{sources['samir']['path']}",
            right_source_id=f"{SOCRATEAI_REPO_ID}@{SOCRATEAI_PINNED_COMMIT}:{sources['socrateai']['path']}",
            left_expected_sha256=left_meta["sha256"],
            right_expected_sha256=right_meta["sha256"],
            left_mapping=samir_merolagani_capture_mapping(),
            right_mapping=socrateai_floorsheet_mapping(),
        )
        comparison = pair["comparison"]
        date_reports[day] = {
            "left_file": left_meta,
            "right_file": right_meta,
            "audit": pair,
            "summary": {
                "samir_input_rows": pair["left_file"]["input_rows"],
                "samir_parsed_rows": pair["left_file"]["parsed_rows"],
                "samir_rejected_rows": pair["left_file"]["rejected_rows"],
                "socrateai_input_rows": pair["right_file"]["input_rows"],
                "socrateai_parsed_rows": pair["right_file"]["parsed_rows"],
                "socrateai_rejected_rows": pair["right_file"]["rejected_rows"],
                "shared_contract_count": comparison.get("shared_contract_count"),
                "exact_shared_contract_count": comparison.get("exact_shared_contract_count"),
                "conflicting_shared_contract_count": comparison.get("conflicting_shared_contract_count"),
                "samir_only_count": len(comparison.get("left_only_contract_keys", [])),
                "socrateai_only_count": len(comparison.get("right_only_contract_keys", [])),
                "samir_totals": comparison.get("left_totals"),
                "socrateai_totals": comparison.get("right_totals"),
                "socrateai_only_quantity": str(sum(
                    (row["quantity"] for row in pair["comparison"].get("right_only_contracts", [])),
                    __import__("decimal").Decimal("0"),
                )),
                "socrateai_only_gross_amount": str(sum(
                    (row["amount"] for row in pair["comparison"].get("right_only_contracts", [])),
                    __import__("decimal").Decimal("0"),
                )),
            },
        }

    return {
        "schema_version": "1.0",
        "audit_status": "review_only_multi_date_archive_comparison",
        "pinned_dates": list(PINNED_DATES),
        "date_reports": date_reports,
        "source_independence_verified": False,
        "daily_capture_completeness_verified": False,
        "source_rights_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "policy": "multi_date_transaction_comparison_only_no_session_or_equity_coverage_promotion",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_pinned_archive_window(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "audit_status": report["audit_status"],
        "dates": {
            day: value["summary"] for day, value in report["date_reports"].items()
        },
        "canonical_promotion_allowed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
