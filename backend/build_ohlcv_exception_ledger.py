#!/usr/bin/env python3
"""Build a deterministic, source-linked quarantine ledger from an OHLCV audit report.

This tool never repairs source rows or chooses a preferred publisher. It preserves
invalid source rows and both sides of cross-source conflicts for human review.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

USER_AUTHORITATIVE_RESOLUTIONS = {
    ("BGWT", "2025-07-28"): {
        "open": "940.00", "high": "992.00", "low": "933.40", "close": "957.17",
        "volume": "14028", "turnover_npr": "13256345.00", "trades": 194,
    },
    ("MEHL", "2025-07-28"): {
        "open": "471.10", "high": "480.50", "low": "460.00", "close": "475.63",
        "volume": "29753", "turnover_npr": "14008898.10", "trades": 333,
    },
    ("RAWA", "2025-07-28"): {
        "open": "796.00", "high": "811.00", "low": "780.30", "close": "796.90",
        "volume": "3165", "turnover_npr": "2515662.50", "trades": 74,
    },
    ("RHGCL", "2025-07-28"): {
        "open": "346.70", "high": "362.00", "low": "341.40", "close": "357.05",
        "volume": "296715", "turnover_npr": "103872614.40", "trades": 1030,
    },
    ("ULHC", "2025-07-28"): {
        "open": "509.00", "high": "515.00", "low": "495.00", "close": "510.75",
        "volume": "32288", "turnover_npr": "16273342.10", "trades": 300,
    },
}

# First-party NEPSE evidence is field-scoped: the captured security-history
# response omits the opening-price field. Keep the raw source rows and record
# only fields explicitly supported by the captured exchange response.
FIELD_SCOPED_NEPSE_RESOLUTIONS = {
    ("API", "2026-11-19"): {
        "supported_fields": {"high": "334.20", "low": "330.00", "close": "331.80", "volume": "105340"},
        "source_reference": "NEPSE security-history raw capture, pinned in data/evidence/raw/nepse/security-history/2026-10-05_to_2026-11-26/symbols",
        "omitted_fields": ["open"],
    },
    ("RHGCL", "2026-11-19"): {
        "supported_fields": {"high": "259.50", "low": "252.10", "close": "258.00", "volume": "9054", "trades": "47"},
        "source_reference": "NEPSE security-history raw capture, pinned in data/evidence/raw/nepse/security-history/2026-10-05_to_2026-11-26/symbols",
        "omitted_fields": ["open"],
    },
}

# HRL's retained project value is user-designated context, not a resolution.
# Keep it beside the independently captured exchange/ShareHub observation so
# reviewers can see the discrepancy without either value being overwritten.
HRL_PROJECT_DISCREPANCY = {
    ("HRL", "2026-11-19"): {
        "project_designated": {"open": "483.00", "low": "483.90"},
        "exchange_observed": {"low": "480.00"},
        "sharehub_observed": {"low": "480.00"},
        "geometry_issue": "project_designated_low_above_open",
        "disposition": "quarantined_unresolved",
        "canonical_promotion_allowed": False,
        "raw_source_rows_modified": False,
    },
}


def build_ledger(report: dict[str, Any], *, external_report: dict[str, Any] | None = None,
                 expected_invalid_rows: int = 1331, expected_conflicts: int = 8) -> dict[str, Any]:
    repositories = report.get("repositories")
    conflicts = report.get("cross_source", {}).get("conflicts")
    if not isinstance(repositories, dict) or not isinstance(conflicts, list):
        raise ValueError("audit report is missing repositories or cross-source conflicts")

    external_lookup = {
        (str(row.get("symbol", "")).upper(), str(row.get("date", ""))): row
        for row in (external_report or {}).get("records", [])
    }
    records: list[dict[str, Any]] = []
    file_lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for repo, snapshot in repositories.items():
        if not snapshot.get("commit_sha"):
            raise ValueError(f"{repo}: pinned commit SHA is missing")
        for item in snapshot.get("files", []):
            file_lookup[(repo, item["symbol"])] = item
            for invalid in item.get("invalid_rows", []):
                raw = invalid.get("row")
                line = invalid.get("line")
                if not isinstance(raw, dict) or not isinstance(line, int):
                    raise ValueError(f"{repo}/{item['path']}: invalid row lacks raw row or line")
                day = raw.get("Date") or raw.get("date")
                if not day:
                    raise ValueError(f"{repo}/{item['path']}:{line}: invalid row lacks date")
                external = external_lookup.get((str(item["symbol"]).upper(), str(day)), {})
                records.append({
                    "exception_id": f"invalid_ohlc:{repo}:{item['symbol']}:{line}",
                    "exception_type": "invalid_ohlc",
                    "symbol": item["symbol"],
                    "trade_date": day,
                    "source_repository": repo,
                    "disposition": "quarantined_unresolved",
                    "reviewer_rationale": invalid.get("error", "Invalid OHLC row; retain exact source values."),
                    "validation_rule_violated": invalid.get("error", "Invalid OHLC row; retain exact source values."),
                    "source_commit_sha": snapshot["commit_sha"],
                    "source_path": item["path"],
                    "source_file_sha256": item["sha256"],
                    "source_csv_line": line,
                    "raw_source_row": raw,
                    "external_corroboration": {
                        key: external.get(key) for key in (
                            "external_status", "external_row", "external_file_sha256",
                            "source_comparisons", "classification"
                        ) if key in external
                    } or None,
                    "evidence_pointer": f"https://github.com/{repo}/blob/{snapshot['commit_sha']}/{item['path']}#L{line}",
                })

    for conflict in conflicts:
        symbol, day = conflict.get("symbol"), conflict.get("date")
        source_rows = conflict.get("source_rows", {})
        if not symbol or not day or len(source_rows) != 2:
            raise ValueError("each cross-source conflict must contain symbol, date and exactly two source rows")
        evidence = {}
        for repo, row in sorted(source_rows.items()):
            snapshot = repositories.get(repo)
            item = file_lookup.get((repo, symbol))
            if not snapshot or not item:
                raise ValueError(f"missing pinned source file metadata for {repo}/{symbol}")
            evidence[repo] = {
                "commit_sha": snapshot["commit_sha"],
                "path": item["path"],
                "file_sha256": item["sha256"],
                "source_csv_line": row.get("source_csv_line"),
                "row": row,
            }
        user_resolution = USER_AUTHORITATIVE_RESOLUTIONS.get((symbol, day))
        field_resolution = FIELD_SCOPED_NEPSE_RESOLUTIONS.get((symbol, day))
        external = external_lookup.get((str(symbol).upper(), str(day)), {})
        disposition = (
            "resolved_with_nepse_field_evidence" if field_resolution else
            "resolved_with_user_authoritative_evidence" if user_resolution else
            "quarantined_unresolved"
        )
        record = {
            "exception_id": f"cross_source_ohlcv_conflict:{symbol}:{day}",
            "exception_type": "cross_source_ohlcv_conflict",
            "symbol": symbol,
            "trade_date": day,
            "source_repository": "|".join(sorted(evidence)),
            "disposition": disposition,
            "reviewer_rationale": (
                "Captured NEPSE security-history evidence supports only the listed fields; opening price is absent from the endpoint response. Preserve all original source rows and do not infer an omitted field."
                if field_resolution else
                "User explicitly designated supplied chart OHLC and floorsheet reconciliation values as final for this exact symbol/date; preserve both original pinned source rows and keep canonical promotion disabled."
                if user_resolution else
                "Pinned archive sources disagree on one or more OHLCV fields; retain both versions pending independent authorized source review."
            ),
            "source_evidence": evidence,
            "external_corroboration": {
                key: external.get(key) for key in (
                    "external_status", "external_row", "external_file_sha256",
                    "source_comparisons", "classification"
                ) if key in external
            } or None,
            "evidence_pointer": (
                ("conversation-memory://user-final-authoritative-2025-07-28-records"
                 if day == "2025-07-28" else
                 "https://github.com/jaljala044/nepse-smc-data/commit/e4d069c6ed292c127e7805b19f98e2837e999073")
                if user_resolution else
                " | ".join(
                    f"https://github.com/{repo}/blob/{repositories[repo]['commit_sha']}/{file_lookup[(repo, symbol)]['path']}#L{evidence[repo]['source_csv_line']}"
                    for repo in sorted(evidence)
                )
            ),
        }
        project_discrepancy = HRL_PROJECT_DISCREPANCY.get((symbol, day))
        if project_discrepancy:
            record["project_owner_context"] = project_discrepancy
            record["reviewer_rationale"] = (
                "HRL project-designated low 483.90 is retained as user-final project context; "
                "NEPSE and ShareHub observations both report 480.00. The designated open is 483.00, "
                "so the project low violates OHLC geometry. Preserve both values and keep the conflict unresolved."
            )
        if field_resolution:
            record["resolution_evidence"] = {
                "authority": "captured_nepse_source_field_scoped",
                "source_reference": field_resolution["source_reference"],
                "supported_fields": field_resolution["supported_fields"],
                "omitted_fields": field_resolution["omitted_fields"],
                "canonical_promotion_allowed": False,
                "raw_source_rows_modified": False,
            }
        elif user_resolution:
            is_july_2025 = day == "2025-07-28"
            record["resolution_evidence"] = {
                "authority": "explicit_user_designation_as_final_and_authoritative",
                "source_file": "NEPSE_Chart_Evidence.pdf" if is_july_2025 else "user-finalized reconciliation record",
                "source_page": 1 if is_july_2025 else None,
                "source_basis": "ShareHub daily OHLC and reconciled floorsheet totals" if is_july_2025 else "user-finalized chart OHLC and floorsheet quantity/turnover",
                "authoritative_values": user_resolution,
                "canonical_promotion_allowed": False,
                "raw_source_rows_modified": False,
            }
        records.append(record)

    records.sort(key=lambda row: (
        row["exception_type"], row["symbol"], row["trade_date"], row["exception_id"]
    ))
    counts = Counter(row["exception_type"] for row in records)
    actual_invalid = counts.get("invalid_ohlc", 0)
    actual_conflicts = counts.get("cross_source_ohlcv_conflict", 0)
    if actual_invalid != expected_invalid_rows or actual_conflicts != expected_conflicts:
        raise ValueError(
            "exception population drift requires review: "
            f"invalid_ohlc={actual_invalid} (expected {expected_invalid_rows}), "
            f"conflicts={actual_conflicts} (expected {expected_conflicts})"
        )
    ids = [row["exception_id"] for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate exception IDs generated")

    return {
        "schema_version": "1.1",
        "source_audit": {
            "generated_at_utc": report.get("generated_at_utc"),
            "mode": report.get("mode"),
            "source_audit_report_sha256": None,
            "repositories": {
                repo: {"commit_sha": snapshot["commit_sha"], "tree_sha": snapshot.get("tree_sha")}
                for repo, snapshot in sorted(repositories.items())
            },
        },
        "counts": {
            "total_exception_records": len(records),
            "invalid_ohlc_rows": actual_invalid,
            "cross_source_conflict_keys": actual_conflicts,
            "unresolved": sum(row["disposition"] == "quarantined_unresolved" for row in records),
            "resolved_with_user_authoritative_evidence": sum(row["disposition"] == "resolved_with_user_authoritative_evidence" for row in records),
            "resolved_with_nepse_field_evidence": sum(row["disposition"] == "resolved_with_nepse_field_evidence" for row in records),
        },
        "exceptions": records,
    }


def write_ledger(report_path: Path, json_path: Path, csv_path: Path, *,
                 external_report_path: Path | None = None,
                 expected_invalid_rows: int = 1331,
                 expected_conflicts: int = 8) -> dict[str, Any]:
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    external_report = json.loads(external_report_path.read_text(encoding="utf-8")) if external_report_path else None
    ledger = build_ledger(
        report, external_report=external_report, expected_invalid_rows=expected_invalid_rows,
        expected_conflicts=expected_conflicts,
    )
    ledger["source_audit"]["source_audit_report_sha256"] = hashlib.sha256(report_bytes).hexdigest()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        fields = sorted({key for record in ledger["exceptions"] for key in record})
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in ledger["exceptions"]:
            writer.writerow({
                key: json.dumps(record[key], ensure_ascii=False, sort_keys=True)
                if isinstance(record.get(key), (dict, list)) else record.get(key, "")
                for key in fields
            })
    return ledger["counts"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="pinned OHLCV audit JSON")
    parser.add_argument("--external-input", type=Path, help="optional SocrateAI cross-check JSON")
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--csv-output", required=True, type=Path)
    parser.add_argument("--expected-invalid-rows", type=int, default=1331)
    parser.add_argument("--expected-conflicts", type=int, default=8)
    args = parser.parse_args()
    counts = write_ledger(
        args.input, args.json_output, args.csv_output, external_report_path=args.external_input,
        expected_invalid_rows=args.expected_invalid_rows,
        expected_conflicts=args.expected_conflicts,
    )
    print(json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
