#!/usr/bin/env python3
"""Manifest and guarded immutable acquisition for public Hugging Face NEPSE files.

The default is manifest-only. Download mode requires explicit rights confirmation,
a positive byte ceiling, and per-file SHA-256 metadata from the Hub.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi, hf_hub_download

DATE_RE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})\.csv(?:\.gz)?$", re.I)


def dated_file(path: str) -> str | None:
    match = DATE_RE.search(path.rsplit("/", 1)[-1])
    if not match:
        return None
    try:
        datetime.strptime(match.group("date"), "%Y-%m-%d")
    except ValueError:
        return None
    return match.group("date")


def field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def lfs_sha256(file_info: Any) -> str | None:
    lfs = field(file_info, "lfs")
    digest = field(lfs, "sha256") if lfs is not None else None
    if digest:
        return str(digest).lower()
    return None


def enumerate_files(repo_id: str, path: str, revision: str) -> tuple[str, list[dict[str, Any]]]:
    api = HfApi(token=False)
    info = api.dataset_info(repo_id, revision=revision, files_metadata=True, token=False)
    commit_sha = info.sha
    entries = api.list_repo_tree(
        repo_id,
        path_in_repo=path.strip("/"),
        recursive=True,
        expand=False,
        revision=commit_sha,
        repo_type="dataset",
        token=False,
    )
    rows = []
    for entry in entries:
        filename = field(entry, "path")
        date = dated_file(filename or "")
        if not filename or date is None:
            continue
        size = field(entry, "size")
        blob_id = field(entry, "blob_id")
        rows.append({
            "repo_id": repo_id,
            "revision": commit_sha,
            "path": filename,
            "date": date,
            "size_bytes": int(size),
            "hub_blob_id": blob_id,
            "lfs_sha256": lfs_sha256(entry),
            "xet_hash": field(entry, "xet_hash"),
        })
    rows.sort(key=lambda row: (row["date"], row["path"]))
    return commit_sha, rows


def verify_file(path: Path, row: dict[str, Any]) -> dict[str, Any]:
    expected = row.get("lfs_sha256")
    if not expected:
        raise ValueError(f"No Hub LFS SHA-256 metadata; refusing verification of {row['path']}")
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            count += len(chunk)
            digest.update(chunk)
    actual = digest.hexdigest()
    if count != row["size_bytes"]:
        raise ValueError(f"Size mismatch for {path}: expected {row['size_bytes']}, got {count}")
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {path}: expected {expected}, got {actual}")
    row.update({
        "local_path": str(path),
        "downloaded_bytes": count,
        "local_sha256": actual,
        "verification": "size_and_hub_lfs_sha256_pass",
    })
    return row


def download_one(row: dict[str, Any], raw_root: Path) -> dict[str, Any]:
    if not row.get("lfs_sha256"):
        raise ValueError(f"Missing LFS SHA-256 metadata for {row['path']}")
    destination = raw_root / row["repo_id"] / row["revision"] / row["path"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        row = verify_file(destination, row)
        row["recovered_existing_file"] = True
        return row

    cached = Path(hf_hub_download(
        repo_id=row["repo_id"],
        filename=row["path"],
        repo_type="dataset",
        revision=row["revision"],
        token=False,
    ))
    fd, temp_name = tempfile.mkstemp(prefix=".partial-", dir=str(destination.parent))
    try:
        with os.fdopen(fd, "wb") as target, cached.open("rb") as source:
            shutil.copyfileobj(source, target, length=1024 * 1024)
            target.flush()
            os.fsync(target.fileno())
        row = verify_file(Path(temp_name), row)
        os.link(temp_name, destination)
        os.unlink(temp_name)
        row["local_path"] = str(destination)
        row["downloaded_at"] = datetime.now(timezone.utc).isoformat()
        return row
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--path", default="floorsheet")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--output", type=Path, default=Path("artifacts/source-manifests"))
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/huggingface"))
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--confirm-data-rights", action="store_true")
    parser.add_argument("--max-total-bytes", type=int, default=0)
    args = parser.parse_args()

    if args.download and not args.confirm_data_rights:
        parser.error("--download requires --confirm-data-rights after rights review")
    if args.download and args.max_total_bytes <= 0:
        parser.error("--download requires a positive --max-total-bytes safety ceiling")

    commit_sha, rows = enumerate_files(args.repo_id, args.path, args.revision)
    total = sum(row["size_bytes"] for row in rows)
    if args.download and total > args.max_total_bytes:
        parser.error(
            f"Manifest size {total} exceeds --max-total-bytes {args.max_total_bytes}"
        )

    args.output.mkdir(parents=True, exist_ok=True)
    stem = f"{args.repo_id.replace('/', '_')}_{commit_sha[:12]}"
    manifest_path = args.output / f"{stem}.jsonl"
    prior: dict[str, dict[str, Any]] = {}
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as previous:
            for line_number, line in enumerate(previous, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    prior[record["path"]] = record
                except (json.JSONDecodeError, KeyError) as exc:
                    parser.error(f"Malformed existing manifest line {line_number}: {exc}")

    with manifest_path.open("a", encoding="utf-8") as manifest:
        for row in rows:
            old = prior.get(row["path"])
            if old and not args.download:
                continue
            if old and args.download and old.get("local_path"):
                old_path = Path(old["local_path"])
                if old_path.exists():
                    verify_file(old_path, row)
                    continue
            row["manifest_observed_at"] = datetime.now(timezone.utc).isoformat()
            if args.download:
                row = download_one(row, args.raw_root)
                row.setdefault("downloaded_at", datetime.now(timezone.utc).isoformat())
            manifest.write(json.dumps(row, sort_keys=True) + "\n")
            manifest.flush()
            os.fsync(manifest.fileno())

    print(json.dumps({
        "repo_id": args.repo_id,
        "revision": commit_sha,
        "dated_file_count": len(rows),
        "manifest_size_bytes": total,
        "manifest_path": str(manifest_path),
        "raw_download_performed": bool(args.download),
        "status": "download_complete" if args.download else "manifest_only",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
