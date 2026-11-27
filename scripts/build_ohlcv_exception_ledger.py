#!/usr/bin/env python3
"""Build a deterministic, read-only row-level OHLCV exception ledger."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

USER_FINAL_KEYS = {
    ("BGWT", "2025-07-28"), ("MEHL", "2025-07-28"),
    ("RAWA", "2025-07-28"), ("RHGCL", "2025-07-28"),
    ("ULHC", "2025-07-28"),
}

def build(archive_audit: dict, external_audit: dict) -> dict:
    repositories = archive_audit["repositories"]
    external = {(r["symbol"], r["date"]): r for r in external_audit.get("records", [])}
    records = []
    for repository, meta in repositories.items():
        for file in meta["files"]:
            for invalid in file.get("invalid_rows", []):
                raw = invalid["row"]
                day = raw["Date"]
                ext = external.get((file["symbol"], day), {})
                records.append({
                    "exception_id": f"invalid_ohlc:{file['symbol']}:{day}:{invalid['line']}",
                    "exception_type": "invalid_ohlc", "symbol": file["symbol"],
                    "trade_date": day, "source_repository": repository,
                    "source_commit_sha": meta["commit_sha"], "source_tree_sha": meta["tree_sha"],
                    "source_path": file["path"], "source_file_sha256": file["sha256"],
                    "source_repository_blob_sha": file.get("repository_blob_sha"),
                    "source_csv_line": invalid["line"], "raw_source_row": raw,
                    "normalized_ohlcv": {k.lower(): raw.get(k) for k in ("Open","High","Low","Close","Volume")},
                    "validation_rule_violated": invalid["error"], "counterpart_source_values": None,
                    "external_corroboration": {k: ext.get(k) for k in ("external_status","external_row","external_file_sha256","source_comparisons","classification")} if ext else None,
                    "disposition": "quarantined_unresolved",
                    "evidence_pointer": f"actions://run/45397942163/artifact/14921283424/{file['path']}#csv-line-{invalid['line']}",
                    "reviewer_rationale": "Pinned source row violates OHLC bounds. Third-party corroboration is not exchange-origin evidence and does not authorize repair."
                })
    for conflict in archive_audit["cross_source"]["conflicts"]:
        symbol, day = conflict["symbol"], conflict["date"]
        evidence = {}
        for repository, row in conflict["source_rows"].items():
            meta = repositories[repository]
            file = next(f for f in meta["files"] if f["symbol"] == symbol)
            evidence[repository] = {
                "commit_sha": meta["commit_sha"], "tree_sha": meta["tree_sha"],
                "path": file["path"], "file_sha256": file["sha256"],
                "repository_blob_sha": file.get("repository_blob_sha"),
                "row": row, "source_csv_line": None
            }
        ext = external.get((symbol, day), {})
        user_final = (symbol, day) in USER_FINAL_KEYS
        records.append({
            "exception_id": f"cross_source_ohlcv_conflict:{symbol}:{day}",
            "exception_type": "cross_source_ohlcv_conflict", "symbol": symbol,
            "trade_date": day, "source_repository": "multiple_pinned_sources",
            "source_evidence": evidence, "counterpart_source_values": conflict["source_rows"],
            "validation_rule_violated": "OHLCV differs for the same normalized symbol/date key",
            "external_corroboration": {k: ext.get(k) for k in ("external_status","external_row","external_file_sha256","source_comparisons","classification")} if ext else None,
            "disposition": "resolved_with_user_authoritative_evidence" if user_final else "quarantined_unresolved",
            "evidence_pointer": "conversation-memory://user-final-authoritative-2025-07-28-records" if user_final else f"actions://run/45397942163/artifact/14921283424/cross-source/{symbol}/{day}",
            "reviewer_rationale": (
                "User explicitly designated the supplied 2025-07-28 record as final and authoritative for this symbol. Preserve the user's OHLC chart reading and floorsheet quantity/turnover; ignore conflicting source values and do not leave this key unresolved because of those conflicts. Original source observations remain preserved."
                if user_final else
                "Pinned source values conflict. Third-party corroboration is not exchange-origin truth; retain both observations and exclude this key from canonical promotion pending independent resolution."
            )
        })
    records.sort(key=lambda r: (r["exception_type"], r["symbol"], r["trade_date"], r.get("source_csv_line") or 0))
    counts = {
        "total_exception_records": len(records),
        "invalid_ohlc_rows": sum(r["exception_type"] == "invalid_ohlc" for r in records),
        "cross_source_conflict_keys": sum(r["exception_type"] == "cross_source_ohlcv_conflict" for r in records),
        "unresolved": sum(r["disposition"] == "quarantined_unresolved" for r in records),
        "resolved_with_user_authoritative_evidence": sum(r["disposition"] == "resolved_with_user_authoritative_evidence" for r in records),
    }
    return {
        "schema_version": "1.1",
        "generated_from": {
            "workflow_run_id": 45397942163, "artifact_id": 14921283424,
            "artifact_sha256": "e1e5e8ac84e1d2ad273b605725c69614693a831117f96a6b8d7f5af2b4c81cb8",
            "source_repositories": {k: {"commit_sha": v["commit_sha"], "tree_sha": v["tree_sha"]} for k, v in repositories.items()}
        },
        "counts": counts,
        "disposition_policy": "No automatic source winner. User-designated final records for five 2025-07-28 symbols supersede source conflicts for those keys only; all other exceptions remain unresolved.",
        "exceptions": records
    }

def write(ledger: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "ohlcv_exception_ledger.json"
    csv_path = output_dir / "ohlcv_exception_ledger.csv"
    json_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = ledger["exceptions"]
    fields = sorted({key for row in rows for key in row})
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict,list)) else v for k,v in row.items()})

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-audit", required=True, type=Path)
    parser.add_argument("--external-audit", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    archive = json.loads(args.archive_audit.read_text(encoding="utf-8"))
    external = json.loads(args.external_audit.read_text(encoding="utf-8"))
    ledger = build(archive, external)
    if ledger["counts"]["total_exception_records"] != 1339 or ledger["counts"]["invalid_ohlc_rows"] != 1331 or ledger["counts"]["cross_source_conflict_keys"] != 8:
        raise SystemExit(f"Unexpected pinned audit totals: {ledger['counts']}")
    write(ledger, args.output_dir)
    print(json.dumps(ledger["counts"], sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
