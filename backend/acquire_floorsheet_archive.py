#!/usr/bin/env python3
"""Enumerate and optionally acquire a dated CSV archive from a public Git repo.

Manifest-only mode is the default. Raw downloads require BOTH --download and
--confirm-data-rights, plus an explicit positive --max-total-bytes ceiling.
Files are immutable: existing destination files are never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATE_RE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})\.csv$", re.I)
GITHUB_API = "https://api.github.com"


def dated_csv(path: str) -> str | None:
    match = DATE_RE.search(path.rsplit("/", 1)[-1])
    if not match:
        return None
    try:
        datetime.strptime(match.group("date"), "%Y-%m-%d")
    except ValueError:
        return None
    return match.group("date")


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def request_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "nepse-archive-auditor/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def enumerate_files(
    owner: str, repo: str, ref: str, prefix: str
) -> tuple[str, list[dict[str, Any]]]:
    repo_info = request_json(f"{GITHUB_API}/repos/{owner}/{repo}")
    branch = ref or repo_info["default_branch"]
    ref_info = request_json(f"{GITHUB_API}/repos/{owner}/{repo}/commits/{branch}")
    commit_sha = ref_info["sha"]
    tree = request_json(
        f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{commit_sha}?recursive=1"
    )
    if tree.get("truncated"):
        raise RuntimeError("Git tree response is truncated; refusing an incomplete manifest")

    prefix = prefix.strip("/")
    rows = []
    for item in tree.get("tree", []):
        path = item.get("path", "")
        date = dated_csv(path)
        if item.get("type") != "blob" or date is None:
            continue
        if prefix and not path.startswith(prefix + "/"):
            continue
        rows.append({
            "repository": f"{owner}/{repo}",
            "commit_sha": commit_sha,
            "path": path,
            "date": date,
            "git_blob_sha1": item["sha"],
            "size_bytes": int(item["size"]),
            "download_url": (
                f"https://raw.githubusercontent.com/{owner}/{repo}/{commit_sha}/{path}"
            ),
        })
    rows.sort(key=lambda row: (row["date"], row["path"]))
    return commit_sha, rows


def verify_local_file(path: Path, row: dict[str, Any]) -> dict[str, Any]:
    sha256 = hashlib.sha256()
    blob_hash = hashlib.sha1()
    count = 0
    with path.open("rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            count += len(chunk)
            sha256.update(chunk)
    blob_hash.update(f"blob {count}\0".encode("ascii"))
    with path.open("rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            blob_hash.update(chunk)
    if count != row["size_bytes"]:
        raise ValueError(f"Existing file size mismatch at {path}")
    if blob_hash.hexdigest() != row["git_blob_sha1"]:
        raise ValueError(f"Existing file Git blob mismatch at {path}")
    row.update({
        "local_path": str(path),
        "downloaded_bytes": count,
        "local_sha256": sha256.hexdigest(),
        "verification": "size_and_git_blob_sha1_pass",
    })
    return row


def download_one(row: dict[str, Any], root: Path) -> dict[str, Any]:
    relative = Path(row["repository"]) / row["commit_sha"] / row["path"]
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        # A previous run may have completed the atomic file promotion but stopped
        # before writing its manifest line. Verify it rather than overwrite it.
        row = verify_local_file(destination, row)
        row["recovered_existing_file"] = True
        return row

    sha256 = hashlib.sha256()
    count = 0
    fd, temp_name = tempfile.mkstemp(prefix=".partial-", dir=str(destination.parent))
    try:
        req = urllib.request.Request(
            row["download_url"],
            headers={"User-Agent": "nepse-archive-auditor/1.0"},
        )
        with os.fdopen(fd, "wb") as output, urllib.request.urlopen(req, timeout=120) as response:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                output.write(chunk)
                sha256.update(chunk)
            output.flush()
            os.fsync(output.fileno())

        blob_hash = hashlib.sha1()
        blob_hash.update(f"blob {count}\0".encode("ascii"))
        with open(temp_name, "rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                blob_hash.update(chunk)

        if count != row["size_bytes"]:
            raise ValueError(f"Size mismatch: expected {row['size_bytes']}, got {count}")
        if blob_hash.hexdigest() != row["git_blob_sha1"]:
            raise ValueError("Git blob SHA-1 mismatch; refusing to promote downloaded bytes")

        # Hard-link creation is atomic and fails rather than replacing an existing file.
        os.link(temp_name, destination)
        os.unlink(temp_name)
        row.update({
            "local_path": str(destination),
            "downloaded_bytes": count,
            "local_sha256": sha256.hexdigest(),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "verification": "size_and_git_blob_sha1_pass",
        })
        return row
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--ref", default="")
    parser.add_argument("--prefix", default="")
    parser.add_argument("--output", type=Path, default=Path("artifacts/source-manifests"))
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--confirm-data-rights", action="store_true")
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/floorsheet"))
    parser.add_argument("--max-total-bytes", type=int, default=0)
    args = parser.parse_args()

    if args.download and not args.confirm_data_rights:
        parser.error("--download requires --confirm-data-rights after rights review")
    if args.download and args.max_total_bytes <= 0:
        parser.error("--download requires a positive --max-total-bytes safety ceiling")

    commit_sha, rows = enumerate_files(args.owner, args.repo, args.ref, args.prefix)
    total = sum(row["size_bytes"] for row in rows)
    if args.download and total > args.max_total_bytes:
        parser.error(
            f"Manifest size {total} exceeds --max-total-bytes {args.max_total_bytes}"
        )

    args.output.mkdir(parents=True, exist_ok=True)
    stem = f"{args.owner}_{args.repo}_{commit_sha[:12]}".replace("/", "_")
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
                    parser.error(
                        f"Existing manifest is malformed at line {line_number}: {exc}"
                    )

    with manifest_path.open("a", encoding="utf-8") as manifest:
        for row in rows:
            old = prior.get(row["path"])
            if old and not args.download:
                continue
            if old and args.download and old.get("local_path"):
                existing_path = Path(old["local_path"])
                if existing_path.exists():
                    verify_local_file(existing_path, row)
                    continue

            row["manifest_observed_at"] = datetime.now(timezone.utc).isoformat()
            if args.download:
                row = download_one(row, args.raw_root)
                row.setdefault("downloaded_at", datetime.now(timezone.utc).isoformat())
            manifest.write(json.dumps(row, sort_keys=True) + "\n")
            manifest.flush()
            os.fsync(manifest.fileno())

    print(json.dumps({
        "repository": f"{args.owner}/{args.repo}",
        "commit_sha": commit_sha,
        "dated_csv_count": len(rows),
        "manifest_size_bytes": total,
        "manifest_path": str(manifest_path),
        "raw_download_performed": bool(args.download),
        "status": "manifest_complete_download_complete" if args.download else "manifest_only",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
