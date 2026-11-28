from __future__ import annotations
import argparse
import json
from pathlib import Path
from app.normalize_floorsheet import normalize_floorsheet_csv

def main():
    parser = argparse.ArgumentParser(description="Normalize one NEPSE floorsheet CSV or a folder of daily CSVs")
    parser.add_argument("input", help="CSV file or directory containing daily floorsheet CSV files")
    parser.add_argument("--source", required=True, help="Dataset/provider name used for provenance")
    parser.add_argument("--max-reject-ratio", type=float, default=0.10)
    parser.add_argument("--validation-registry", help="shared SQLite validation registry path")
    args = parser.parse_args()

    path = Path(args.input)
    candidates = sorted(
        list(path.rglob("*.csv")) + list(path.rglob("*.csv.gz"))
    ) if path.is_dir() else [path]
    if not candidates:
        parser.error("No CSV files found")
    registry = None
    if args.validation_registry:
        try:
            from nepse_shared_validation import ValidationRegistry
        except ImportError:
            parser.error("Install nepse-shared-validation before using --validation-registry")
        registry = ValidationRegistry(args.validation_registry)

    results = []
    failures = []
    for candidate in candidates:
        try:
            results.append(normalize_floorsheet_csv(
                candidate, source=args.source,
                max_reject_ratio=args.max_reject_ratio, registry=registry,
            ))
        except Exception as exc:
            failures.append({"file": str(candidate), "error": f"{type(exc).__name__}: {exc}"})
    report = {
        "source": args.source, "files_considered": len(candidates),
        "files_normalized": len(results), "files_failed": len(failures),
        "results": results, "failures": failures,
    }
    print(json.dumps(report, indent=2))
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
