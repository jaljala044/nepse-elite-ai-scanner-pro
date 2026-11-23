from __future__ import annotations
import argparse
import json
from pathlib import Path
from app.normalize_indices import normalize_sector_index_csv

def main():
    parser = argparse.ArgumentParser(description="Normalize one NEPSE sector-index CSV or a folder")
    parser.add_argument("input", help="CSV/GZ file or directory containing daily index files")
    parser.add_argument("--source", required=True)
    parser.add_argument("--max-reject-ratio", type=float, default=0.10)
    args = parser.parse_args()
    path = Path(args.input)
    candidates = sorted(list(path.rglob("*.csv")) + list(path.rglob("*.csv.gz"))) if path.is_dir() else [path]
    if not candidates:
        parser.error("No index CSV or CSV.GZ files found")
    results, failures = [], []
    for file in candidates:
        try:
            results.append(normalize_sector_index_csv(file, source=args.source,
                                                      max_reject_ratio=args.max_reject_ratio))
        except Exception as exc:
            failures.append({"file": str(file), "error": f"{type(exc).__name__}: {exc}"})
    print(json.dumps({"files_considered": len(candidates), "files_normalized": len(results),
                      "files_failed": len(failures), "results": results, "failures": failures}, indent=2))
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
