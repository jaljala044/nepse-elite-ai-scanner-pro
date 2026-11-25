"""CLI for generating a read-only, immutable-revision Hugging Face inventory."""
from __future__ import annotations

import argparse
import json
from datetime import date

from app.hf_dataset_collector import DATASETS, collect_hf_datasets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", action="append", choices=sorted(DATASETS),
                        help="Dataset key; repeat to select multiple. Defaults to all.")
    parser.add_argument("--max-files", type=int, default=10000)
    parser.add_argument("--from-date", type=date.fromisoformat)
    parser.add_argument("--to-date", type=date.fromisoformat)
    parser.add_argument("--revision", default="main",
                        help="Requested ref; it is resolved to a commit SHA before listing.")
    args = parser.parse_args()
    result = collect_hf_datasets(
        dataset_keys=args.dataset,
        download=False,
        max_files=args.max_files,
        from_date=args.from_date,
        to_date=args.to_date,
        revision=args.revision,
    )
    print(json.dumps({
        "manifest_path": result["manifest_path"],
        "retrieved_at_utc": result["retrieved_at_utc"],
        "datasets": {
            key: {
                "repo": value["repo"],
                "revision": value["revision"],
                "listing_complete": value["listing_complete"],
                "inventory_complete": value["inventory_complete"],
                "files_found": value["files_found"],
                "files_considered": value["files_considered"],
            }
            for key, value in result["datasets"].items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
