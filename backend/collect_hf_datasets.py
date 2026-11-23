from __future__ import annotations
import argparse
import json
from datetime import date
from app.hf_dataset_collector import DATASETS, collect_hf_datasets

def parse_date(value: str | None):
    return date.fromisoformat(value) if value else None

def main():
    parser = argparse.ArgumentParser(description="Inventory or download public Hugging Face NEPSE datasets")
    parser.add_argument("--dataset", action="append", choices=sorted(DATASETS),
                        help="Repeat to select datasets; default is all supported datasets")
    parser.add_argument("--download", action="store_true",
                        help="Actually download files. Without this flag, only inventory files.")
    parser.add_argument("--max-total-mb", type=int, default=50,
                        help="Total download budget in MiB (default 50)")
    parser.add_argument("--max-file-mb", type=int, default=100,
                        help="Per-file download ceiling in MiB (default 100)")
    parser.add_argument("--max-files", type=int, default=10000,
                        help="Maximum number of files per run")
    parser.add_argument("--from-date", help="Optional inclusive YYYY-MM-DD filter")
    parser.add_argument("--to-date", help="Optional inclusive YYYY-MM-DD filter")
    args = parser.parse_args()
    result = collect_hf_datasets(
        args.dataset, download=args.download,
        max_total_bytes=args.max_total_mb * 1024 * 1024,
        max_file_bytes=args.max_file_mb * 1024 * 1024,
        max_files=args.max_files,
        from_date=parse_date(args.from_date), to_date=parse_date(args.to_date),
    )
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
