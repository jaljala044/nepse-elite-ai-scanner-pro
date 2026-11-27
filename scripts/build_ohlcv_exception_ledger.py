#!/usr/bin/env python3
"""Build a read-only OHLCV exception ledger from pinned audit JSON artifacts."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

EXPECTED = {"invalid_ohlc": 1331, "cross_source_ohlcv_conflict": 8}

# These five 2025-07-28 records are explicitly user-designated authoritative.
# Values are transcribed from the user-provided NEPSE_Chart_Evidence.pdf, p. 1:
# ShareHub daily OHLC plus reconciled ShareHub floorsheet shares/amount/trades.
# This is a row-specific resolution only; it does not authorize source-file edits
# or canonical dataset promotion.
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

def load_json(path: Path) -> dict:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            required = {"ohlcv-archive-audit.json", "ohlcv-socrateai-crosscheck.json"}
            if not required.issubset(names):
                raise ValueError(f"artifact ZIP missing {sorted(required - names)}")
            return {name: json.loads(archive.read(name)) for name in required}
    raise ValueError("provide the pinned audit artifact ZIP")

def build(archive_audit: dict, external_audit: dict, artifact_id: int,
          artifact_sha256: str) -> dict:
    repos = archive_audit["repositories"]
    external = {(r["symbol"], r["date"]): r for r in external_audit["records"]}
    records = []
    for repo, meta in repos.items():
        for file_record in meta["files"]:
            for invalid in file_record.get("invalid_rows", []):
                raw = invalid["row"]
                date = raw.get("Date")
                corroboration = external.get((file_record["symbol"], date))
                records.append({
                    "exception_id": f"invalid_ohlc:{repo}:{file_record['symbol']}:{date}:{invalid['line']}",
                    "exception_type": "invalid_ohlc", "symbol": file_record["symbol"],
                    "trade_date": date, "source_repository": repo,
                    "source_commit_sha": meta["commit_sha"], "source_path": file_record["path"],
                    "source_file_sha256": file_record["sha256"], "source_csv_line": invalid["line"],
                    "raw_source_row": raw,
                    "normalized_source_row": {"date": date, "open": raw.get("Open"),
                        "high": raw.get("High"), "low": raw.get("Low"),
                        "close": raw.get("Close"), "volume": raw.get("Volume")},
                    "validation_rule_violated": invalid["error"], "counterpart_source_values": None,
                    "external_corroboration": corroboration or {"status": "not_found_in_crosscheck"},
                    "disposition": "quarantined_unresolved",
                    "evidence_pointer": f"workflow-artifact:{artifact_id}/ohlcv-archive-audit.json#{file_record['symbol']}:{date}:line:{invalid['line']}",
                    "reviewer_rationale": "Invalid OHLC bounds remain unresolved. Third-party corroboration is not exchange-origin truth; no repair or source selection is authorized.",
                    "point_in_time_available_at": archive_audit["generated_at_utc"],
                })
    for conflict in archive_audit["cross_source"]["conflicts"]:
        symbol, date = conflict["symbol"], conflict["date"]
        evidence = {}
        for repo, row in conflict["source_rows"].items():
            file_record = next(f for f in repos[repo]["files"] if f["symbol"] == symbol)
            evidence[repo] = {"commit_sha": repos[repo]["commit_sha"],
                "path": file_record["path"], "file_sha256": file_record["sha256"],
                "row": row, "source_csv_line": None}
        user_resolution = USER_AUTHORITATIVE_RESOLUTIONS.get((symbol, date))
        record = {
            "exception_id": f"cross_source_ohlcv_conflict:{symbol}:{date}",
            "exception_type": "cross_source_ohlcv_conflict", "symbol": symbol,
            "trade_date": date,
            "source_repository": "|".join(sorted(conflict["source_rows"])),
            "source_commit_sha": None, "source_path": None, "source_file_sha256": None,
            "source_csv_line": None, "raw_source_row": None, "normalized_source_row": None,
            "validation_rule_violated": "OHLCV values differ for the same symbol/date across pinned source archives",
            "counterpart_source_values": conflict["source_rows"], "source_evidence": evidence,
            "external_corroboration": external.get((symbol, date), {"status": "not_found_in_crosscheck"}),
            "disposition": "resolved_with_user_authoritative_evidence" if user_resolution else "quarantined_unresolved",
            "evidence_pointer": f"workflow-artifact:{artifact_id}/ohlcv-archive-audit.json#conflict:{symbol}:{date}",
            "reviewer_rationale": (
                "Resolved using the user's explicit final/authoritative instruction and supplied chart/floorsheet evidence. "
                "Both source rows remain preserved; this row-level resolution does not authorize canonical promotion."
                if user_resolution else
                "Both pinned source values are retained. No winner is selected; third-party corroboration is not exchange-origin truth."
            ),
            "point_in_time_available_at": archive_audit["generated_at_utc"],
        }
        if user_resolution:
            record["resolution_evidence"] = {
                "authority": "explicit_user_designation_as_final_and_authoritative",
                "source_file": "NEPSE_Chart_Evidence.pdf",
                "source_page": 1,
                "source_basis": "ShareHub daily OHLC and ShareHub floorsheet quantity/turnover/trade-count reconciliation",
                "authoritative_values": user_resolution,
                "canonical_promotion_allowed": False,
                "raw_source_rows_modified": False,
            }
        records.append(record)
    counts = Counter(r["exception_type"] for r in records)
    if counts != Counter(EXPECTED):
        raise ValueError(f"pinned audit counts changed: {dict(counts)}")
    ids = [r["exception_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate exception IDs")
    return {
        "schema_version": "1.0.0", "generated_at_utc": archive_audit["generated_at_utc"],
        "audit_artifact": {"workflow_run_id": 45397942163, "artifact_id": artifact_id,
                           "artifact_sha256": artifact_sha256},
        "pinned_sources": {repo: {"commit_sha": meta["commit_sha"], "tree_sha": meta["tree_sha"]}
                           for repo, meta in repos.items()},
        "counts": {"total_exception_records": len(records),
                   "invalid_ohlc_rows": counts["invalid_ohlc"],
                   "cross_source_conflict_keys": counts["cross_source_ohlcv_conflict"]},
        "disposition_policy": "Unresolved exceptions remain quarantined. Five explicitly user-authoritative 2025-07-28 conflicts are row-resolved with preserved source values; no source rows are modified and no canonical promotion is authorized.",
        "exceptions": records,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-zip", required=True, type=Path)
    parser.add_argument("--artifact-id", required=True, type=int)
    parser.add_argument("--artifact-sha256", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.artifact_zip.read_bytes()).hexdigest() != args.artifact_sha256:
        raise SystemExit("artifact ZIP SHA-256 mismatch")
    loaded = load_json(args.artifact_zip)
    ledger = build(loaded["ohlcv-archive-audit.json"], loaded["ohlcv-socrateai-crosscheck.json"],
                   args.artifact_id, args.artifact_sha256)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "ohlcv_exception_ledger.json"
    csv_path = args.output_dir / "ohlcv_exception_ledger.csv"
    json_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = sorted({key for row in ledger["exceptions"] for key in row})
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in ledger["exceptions"]:
            writer.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True)
                             if isinstance(v, (dict, list)) else v for k, v in row.items()})
    print(f"PASS: {ledger['counts']} -> {json_path} and {csv_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
