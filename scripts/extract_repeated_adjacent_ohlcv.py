#!/usr/bin/env python3
"""Read-only extraction of identical adjacent OHLCV rows from pinned archive checkouts."""
from __future__ import annotations
import argparse, csv, hashlib, json
from pathlib import Path

FIELDS = ("Open", "High", "Low", "Close", "Volume")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def extract(repo: str, commit: str, root: Path) -> list[dict]:
    out = []
    files = sorted(root.rglob("*_OHLCV.csv"))
    for path in files:
        rel = path.relative_to(root).as_posix()
        digest = sha256(path)
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            previous = None
            previous_line = None
            for line, row in enumerate(reader, start=2):
                current = {k: (row.get(k) or "").strip() for k in FIELDS}
                date = (row.get("Date") or row.get("date") or "").strip()
                symbol = (row.get("Symbol") or row.get("symbol") or path.stem.replace("_OHLCV", "")).strip()
                if previous is not None and current == previous["ohlcv"]:
                    out.append({
                        "repository": repo, "commit_sha": commit, "path": rel,
                        "file_sha256": digest, "symbol": symbol,
                        "previous_date": previous["date"], "current_date": date,
                        "previous_csv_line": previous_line, "current_csv_line": line,
                        "ohlcv": current,
                        "classification": "calendar_status_unverified_review_flag",
                    })
                previous, previous_line = {"date": date, "ohlcv": current}, line
    return out

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", action="append", nargs=3, metavar=("REPO", "COMMIT", "ROOT"), required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    all_rows = []
    per_source = {}
    for repo, commit, root in args.source:
        rows = extract(repo, commit, Path(root))
        per_source[repo] = len(rows)
        all_rows.extend(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    csv_path = args.out / "repeated_adjacent_ohlcv_candidates.csv"
    fields = ["repository", "commit_sha", "path", "file_sha256", "symbol",
              "previous_date", "current_date", "previous_csv_line", "current_csv_line",
              "ohlcv", "classification"]
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({**row, "ohlcv": json.dumps(row["ohlcv"], sort_keys=True)})
    summary = {
        "method": "identical OHLCV signatures on consecutive CSV rows; no session inference",
        "source_counts": per_source, "total_candidates": len(all_rows),
        "calendar_status": "not_verified_primary_exchange_evidence_missing",
        "classification": "review_only_not_invalid",
        "source_files_read_only": True,
    }
    (args.out / "repeated_adjacent_ohlcv_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
