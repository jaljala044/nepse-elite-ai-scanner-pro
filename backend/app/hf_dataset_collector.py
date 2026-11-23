"""Read-only Hugging Face NEPSE dataset inventory and bounded downloader.

Bulk data is written to the runtime data/raw directory, never to Git commits.
Public datasets only; no token is required for public repositories.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

import httpx

HF_API = "https://huggingface.co/api/datasets"
HF_RESOLVE = "https://huggingface.co/datasets"
REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = REPO_ROOT / "data" / "raw" / "huggingface"
TIMEOUT = httpx.Timeout(60.0, connect=15.0)
HEADERS = {"User-Agent": "NEPSE-ELITE-AI-SCANNER/0.3 (read-only dataset collector)"}

DATASETS: dict[str, dict[str, Any]] = {
    "floorsheet_indices_2024": {
        "repo": "urekmazino69/Nepse-floorsheet-and-indices",
        "folders": ("floorsheet/", "indices/"),
        "extensions": (".csv", ".csv.gz"),
        "notes": "Daily transaction-level floorsheet and sector-index CSV files; publisher states 2024-01-02 through 2026-08-26.",
    },
    "market_data_2026": {
        "repo": "AnkitSanjyal/nepse-market-data",
        "folders": (
            "floorsheet/", "index_intraday/", "eod_history_ext/",
            "eod_price/", "bars_1m/", "broker_flow_daily/", "daily_stats/",
        ),
        "extensions": (".parquet", ".csv", ".json"),
        "notes": "Publisher describes long EOD history plus recent floorsheet and derived datasets; floorsheet has a documented 2026-08-26 through 2026-11-18 gap.",
    },
    "market_data_floorsheet": {
        "repo": "AnkitSanjyal/nepse-market-data",
        "folders": ("floorsheet/",),
        "extensions": (".parquet", ".csv"),
        "notes": "Trade-level NEPSE floorsheet partitions from 2026-08-19; publisher documents missing sessions from 2026-08-26 through 2026-11-18.",
    },
    "market_data_eod": {
        "repo": "AnkitSanjyal/nepse-market-data",
        "folders": ("eod_history_ext/", "eod_price/"),
        "extensions": (".parquet", ".csv"),
        "notes": "Extended ShareSansar EOD and recent NEPSE EOD tables; separate sources and schema; do not merge without reconciliation.",
    },
    "market_data_broker_flow": {
        "repo": "AnkitSanjyal/nepse-market-data",
        "folders": ("broker_flow_daily/",),
        "extensions": (".parquet", ".csv"),
        "notes": "Derived symbol x broker x day flow, not raw exchange orders or beneficial-owner identity.",
    },
    "market_data_indices": {
        "repo": "AnkitSanjyal/nepse-market-data",
        "folders": ("index_intraday/",),
        "extensions": (".parquet", ".csv"),
        "notes": "Captured intraday index data with limited session coverage.",
    },
}

def _safe_repo_dir(repo: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", repo.replace("/", "__"))

def _safe_relative_path(path: str) -> Path:
    pure = PurePosixPath(path)
    if pure.is_absolute() or not pure.parts or any(p in ("", ".", "..") for p in pure.parts):
        raise ValueError(f"Unsafe repository path: {path!r}")
    return Path(*pure.parts)

def _extract_date(path: str) -> date | None:
    candidates = re.findall(r"(?<!\d)(20\d{2}-\d{2}-\d{2})(?!\d)", path)
    if not candidates:
        candidates = re.findall(r"(?<!\d)(20\d{2}_\d{2}_\d{2})(?!\d)", path)
    for raw in candidates:
        try:
            return date.fromisoformat(raw.replace("_", "-"))
        except ValueError:
            continue
    return None

def _is_candidate(dataset_key: str, path: str) -> bool:
    spec = DATASETS[dataset_key]
    lower = path.lower()
    return (
        lower.startswith(tuple(p.lower() for p in spec["folders"]))
        and lower.endswith(tuple(e.lower() for e in spec["extensions"]))
    )

def _matches_date(path: str, start: date | None, end: date | None) -> bool:
    if start is None and end is None:
        return True
    found = _extract_date(path)
    if found is None:
        # Partitioned Parquet paths often encode the date as date=YYYY-MM-DD.
        return False
    return (start is None or found >= start) and (end is None or found <= end)

def _next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        match = re.search(r"<([^>]+)>\s*;\s*rel=[\"']next[\"']", part)
        if match:
            return match.group(1)
    return None

def _item_path(item: dict[str, Any], folder: str) -> str:
    raw_path = item.get("path") or item.get("rfilename") or item.get("name") or ""
    path = str(raw_path).lstrip("/")
    if path and "/" not in path:
        path = folder.rstrip("/") + "/" + path
    return path


def list_dataset_files(client: httpx.Client, dataset_key: str, revision: str = "main") -> list[dict[str, Any]]:
    if dataset_key not in DATASETS:
        raise ValueError(f"Unknown dataset key: {dataset_key}")
    spec = DATASETS[dataset_key]
    repo = spec["repo"]
    collected: dict[str, dict[str, Any]] = {}

    # List each declared top-level data folder explicitly. Some Hub tree responses
    # return only root directory entries when a recursive query is not honored.
    for folder in spec["folders"]:
        url = (
            f"{HF_API}/{quote(repo, safe='/')}/tree/"
            f"{quote(revision, safe='')}/{quote(folder.rstrip('/'), safe='/')}"
        )
        params: dict[str, Any] | None = {
            "recursive": "true", "expand": "false", "limit": 1000
        }
        seen_cursors: set[str] = set()
        pages = 0
        while url:
            pages += 1
            if pages > 100:
                raise RuntimeError(f"Dataset tree pagination exceeded 100 pages for {folder}")
            response = client.get(url, params=params)
            if response.status_code == 404:
                # A declared table can legitimately have no published files yet
                # (for example an intraday table before the first captured session).
                break
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list):
                items, cursor = payload, None
            elif isinstance(payload, dict):
                items = payload.get("items", payload.get("files", payload.get("data", [])))
                cursor = payload.get("cursor")
            else:
                raise ValueError("Unexpected Hugging Face tree response")
            if not isinstance(items, list):
                raise ValueError("Unexpected Hugging Face tree items payload")

            for item in items:
                if not isinstance(item, dict):
                    continue
                item_type = str(item.get("type", "")).lower()
                if item_type in ("directory", "dir", "tree", "folder"):
                    continue
                path = _item_path(item, folder)
                if not path or not _is_candidate(dataset_key, path):
                    continue
                # A file-like path with a declared extension is the final filter;
                # this also tolerates Hub response variants that omit type.
                size = item.get("size")
                if size is None and isinstance(item.get("lfs"), dict):
                    size = item["lfs"].get("size")
                collected[path] = {
                    "path": path,
                    "size": int(size or 0),
                    "oid": item.get("oid") or item.get("blob_id") or item.get("sha"),
                    "lfs": item.get("lfs"),
                }

            next_url = _next_link(response.headers.get("Link"))
            if next_url:
                url, params = next_url, None
            elif cursor and cursor not in seen_cursors:
                seen_cursors.add(cursor)
                params = {
                    "recursive": "true", "expand": "false", "limit": 1000,
                    "cursor": cursor,
                }
            else:
                break

    return sorted(collected.values(), key=lambda item: item["path"])

def _download_one(
    client: httpx.Client, repo: str, revision: str, item: dict[str, Any],
    dataset_key: str, max_file_bytes: int, total_remaining: int,
) -> dict[str, Any]:
    path = str(item["path"])
    expected_size = int(item.get("size") or 0)
    if expected_size and expected_size > max_file_bytes:
        return {"path": path, "status": "skipped_file_limit", "expected_size": expected_size}
    if expected_size and expected_size > total_remaining:
        return {"path": path, "status": "skipped_total_budget", "expected_size": expected_size}
    relative = _safe_relative_path(path)
    destination = RAW_ROOT / _safe_repo_dir(repo) / revision / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(destination.suffix + ".part")
    url = f"{HF_RESOLVE}/{quote(repo, safe='/')}/resolve/{quote(revision, safe='')}/{quote(path, safe='/')}?download=true"
    digest = hashlib.sha256()
    byte_count = 0
    try:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with temp.open("wb") as handle:
                for chunk in response.iter_bytes(1024 * 1024):
                    byte_count += len(chunk)
                    if byte_count > max_file_bytes or byte_count > total_remaining:
                        raise ValueError("Download exceeded configured byte budget")
                    digest.update(chunk)
                    handle.write(chunk)
        temp.replace(destination)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    return {
        "path": path, "status": "downloaded", "bytes": byte_count,
        "sha256": digest.hexdigest(), "hub_oid": item.get("oid"),
        "local_path": str(destination.relative_to(REPO_ROOT)),
        "download_url": url,
    }

def collect_hf_datasets(
    dataset_keys: list[str] | None = None,
    *,
    download: bool = False,
    max_total_bytes: int = 50 * 1024 * 1024,
    max_file_bytes: int = 100 * 1024 * 1024,
    max_files: int = 10000,
    from_date: date | None = None,
    to_date: date | None = None,
    revision: str = "main",
) -> dict[str, Any]:
    selected = dataset_keys or list(DATASETS)
    unknown = set(selected) - set(DATASETS)
    if unknown:
        raise ValueError("Unknown datasets: " + ", ".join(sorted(unknown)))
    if max_total_bytes < 0 or max_file_bytes < 1 or max_files < 1:
        raise ValueError("Download limits must be positive (total budget may be zero)")
    if from_date and to_date and from_date > to_date:
        raise ValueError("from_date must not be after to_date")

    results: dict[str, Any] = {}
    with httpx.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
        remaining = max_total_bytes
        downloaded_count = 0
        for key in selected:
            spec = DATASETS[key]
            files = list_dataset_files(client, key, revision=revision)
            files = [f for f in files if _matches_date(f["path"], from_date, to_date)]
            selected_files = files[:max_files]
            records: list[dict[str, Any]] = []
            if download:
                for item in selected_files:
                    if downloaded_count >= max_files:
                        records.append({"path": item["path"], "status": "skipped_global_file_limit"})
                        continue
                    try:
                        result = _download_one(
                            client, spec["repo"], revision, item, key,
                            max_file_bytes, remaining
                        )
                    except Exception as exc:
                        result = {"path": item["path"], "status": "error",
                                  "error": f"{type(exc).__name__}: {exc}"}
                    records.append(result)
                    if result.get("status") == "downloaded":
                        remaining -= result["bytes"]
                        downloaded_count += 1
            results[key] = {
                "repo": spec["repo"], "revision": revision, "notes": spec["notes"],
                "files_found": len(files), "files_considered": len(selected_files),
                "estimated_bytes": sum(f["size"] for f in selected_files),
                "records": records if download else selected_files,
            }

    manifest = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "bounded_download" if download else "inventory_only",
        "max_total_bytes": max_total_bytes, "max_file_bytes": max_file_bytes,
        "max_files": max_files, "from_date": str(from_date) if from_date else None,
        "to_date": str(to_date) if to_date else None, "datasets": results,
        "data_root": str(RAW_ROOT.relative_to(REPO_ROOT)),
        "warning": "Dataset publisher claims and file metadata are provenance, not independent verification. Validate schemas, coverage, corporate actions and overlap before analytics.",
    }
    manifest_dir = RAW_ROOT / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"hf_inventory_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path.relative_to(REPO_ROOT))
    return manifest
