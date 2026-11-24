#!/usr/bin/env python3
"""Compare Urek and SocrateAI floorsheet transaction rows across all shared dates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from compare_floorsheet_samples import compare_samples, read_rows, sha256_file


def compare_windows(urek_manifest_path: str | Path, socrateai_manifest_path: str | Path) -> dict[str, Any]:
    urek_manifest = json.loads(Path(urek_manifest_path).read_text(encoding="utf-8"))
    soc_manifest = json.loads(Path(socrateai_manifest_path).read_text(encoding="utf-8"))
    urek_files = {str(row["date"]): row for row in urek_manifest.get("files", [])}
    soc_files = {str(row["date"]): row for row in soc_manifest.get("files", [])}
    if len(urek_files) != len(urek_manifest.get("files", [])):
        raise ValueError("Urek manifest has duplicate dates")
    if len(soc_files) != len(soc_manifest.get("files", [])):
        raise ValueError("SocrateAI manifest has duplicate dates")
    common_dates = sorted(set(urek_files) & set(soc_files))
    results = []
    errors = []
    for day in common_dates:
        urek_entry = urek_files[day]
        soc_entry = soc_files[day]
        try:
            repository_root = Path.cwd().resolve()
            urek_path = Path(urek_entry.get("local_path") or urek_entry.get("repository_path") or "")
            soc_path = Path(soc_entry.get("local_path") or soc_entry.get("repository_path") or "")
            if not urek_path.is_absolute():
                urek_path = (repository_root / urek_path).resolve()
            if not soc_path.is_absolute():
                soc_path = (repository_root / soc_path).resolve()
            if not urek_path.is_file() and urek_entry.get("repository_path"):
                urek_path = (repository_root / urek_entry["repository_path"]).resolve()
            if not soc_path.is_file() and soc_entry.get("repository_path"):
                soc_path = (repository_root / soc_entry["repository_path"]).resolve()
            if not urek_path.is_file() or not soc_path.is_file():
                raise FileNotFoundError("one or both raw files are missing")
            for source_name, source_path, entry in (
                ("urek", urek_path, urek_entry),
                ("socrateai", soc_path, soc_entry),
            ):
                expected_hash = entry.get("local_sha256")
                if expected_hash and sha256_file(source_path) != expected_hash:
                    raise ValueError(f"{source_name} local SHA-256 differs from acquisition manifest")
            result = compare_samples(read_rows(urek_path), read_rows(soc_path), day)
            contract = result["contract_number_comparison"]
            results.append({
                "date": day,
                "urek_row_count": result["urek"]["row_count"],
                "socrateai_row_count": result["socrateai"]["row_count"],
                "shared_contracts": contract["shared_contracts"],
                "urek_only_contracts": contract["urek_only_contracts"],
                "socrateai_only_contracts": contract["socrateai_only_contracts"],
                "urek_duplicate_contracts": len(contract["urek_duplicate_contract_numbers"]),
                "socrateai_duplicate_contracts": len(contract["socrateai_duplicate_contract_numbers"]),
                "shared_field_mismatch_count": result["shared_field_mismatch_count"],
                "date_error_count": result["date_error_count"],
                "status": result["cross_source_status"],
                "urek_sha256": urek_entry.get("local_sha256"),
                "socrateai_sha256": soc_entry.get("local_sha256"),
            })
        except Exception as exc:
            errors.append({"date": day, "error": f"{type(exc).__name__}: {exc}"})
    mismatch_dates = [row["date"] for row in results if row["status"] != "EXACT_MATCH_ON_SHARED_TRANSACTION_FIELDS"]
    total_shared = sum(row["shared_contracts"] for row in results)
    total_mismatches = sum(row["shared_field_mismatch_count"] for row in results)
    total_urek_only = sum(row["urek_only_contracts"] for row in results)
    total_soc_only = sum(row["socrateai_only_contracts"] for row in results)
    status = (
        "all_shared_dates_exact_match"
        if common_dates and not mismatch_dates and not errors
        else "cross_source_mismatch_or_audit_error"
    )
    return {
        "urek_repository": urek_manifest.get("repo_id"),
        "urek_commit": urek_manifest.get("resolved_commit_sha"),
        "socrateai_repository": soc_manifest.get("repository"),
        "socrateai_commit": soc_manifest.get("resolved_commit_sha"),
        "urek_available_dates": len(urek_files),
        "socrateai_available_dates": len(soc_files),
        "common_date_count": len(common_dates),
        "urek_only_dates": sorted(set(urek_files) - set(soc_files)),
        "socrateai_only_dates": sorted(set(soc_files) - set(urek_files)),
        "total_shared_contracts": total_shared,
        "total_urek_only_contracts": total_urek_only,
        "total_socrateai_only_contracts": total_soc_only,
        "total_shared_field_mismatches": total_mismatches,
        "mismatch_date_count": len(mismatch_dates),
        "mismatch_dates": mismatch_dates,
        "audit_error_count": len(errors),
        "audit_errors": errors,
        "daily_comparisons": results,
        "status": status,
        "provenance_independence": "not_established; both publishers may share an upstream source",
        "canonical_promotion_allowed": False,
        "limitations": [
            "Only shared transaction fields are compared; Urek time, sector and id fields are not present in the SocrateAI schema.",
            "An exact match on overlapping dates does not prove either archive is complete or independently sourced.",
            "No source rows are merged, deduplicated or corrected.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--urek-manifest", type=Path, required=True)
    parser.add_argument("--socrateai-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = compare_windows(args.urek_manifest, args.socrateai_manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "urek_available_dates": report["urek_available_dates"],
        "socrateai_available_dates": report["socrateai_available_dates"],
        "common_date_count": report["common_date_count"],
        "total_shared_contracts": report["total_shared_contracts"],
        "total_shared_field_mismatches": report["total_shared_field_mismatches"],
        "mismatch_date_count": report["mismatch_date_count"],
        "audit_error_count": report["audit_error_count"],
        "status": report["status"],
    }, indent=2))
    if report["status"] != "all_shared_dates_exact_match":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
