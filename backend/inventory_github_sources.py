"""Inventory NEPSE GitHub archives without downloading large data files.

Uses GitHub's repository/tree API, records the exact commit and tree SHA, and emits
per-category file counts, byte totals, path-date coverage and a file-level manifest.
Set GITHUB_TOKEN for private repositories (for example, jaljala044/nepse-automation).
No files are imported or modified by this command.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

API = "https://api.github.com"
DEFAULT_REPOS = [
    "jaljala044/nepse-smc-data",
    "jaljala044/nepse-history-starter",
    "jaljala044/nepse-automation",
    "socrateai-official/nepse-open-data",
    "SamirWagle/Nepse-All-Scraper",
    "srijankarki07/nepse-data",
]
TIMEOUT = httpx.Timeout(45.0, connect=15.0)


def category(path: str) -> str:
    p = path.lower()
    if "floorsheet" in p:
        return "floorsheet"
    if "broker" in p or "broker_flow" in p:
        return "broker_flow_or_summary"
    if "ohlc" in p or "price" in p or "close" in p:
        return "ohlcv_or_prices"
    if "index" in p or "sector" in p:
        return "indices_or_sectors"
    if any(x in p for x in ("dividend", "right-share", "corporate_action")):
        return "corporate_actions"
    if "symbol" in p or "company_list" in p or "master" in p:
        return "symbol_master"
    return "other"


def path_date(path: str) -> str | None:
    match = re.search(r"(?<!\d)(20\d{2}-\d{2}-\d{2})(?!\d)", path)
    if not match:
        match = re.search(r"(?<!\d)(20\d{2}_\d{2}_\d{2})(?!\d)", path)
    if not match:
        return None
    raw = match.group(1).replace("_", "-")
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def inventory_repo(client: httpx.Client, repo: str) -> dict[str, Any]:
    headers = {"Accept": "application/vnd.github+json"}
    default_resp = client.get(f"{API}/repos/{repo}", headers=headers)
    default_resp.raise_for_status()
    default_branch = default_resp.json()["default_branch"]
    ref_resp = client.get(
        f"{API}/repos/{repo}/git/ref/heads/{default_branch}",
        headers=headers,
    )
    ref_resp.raise_for_status()
    commit_sha = ref_resp.json()["object"]["sha"]
    commit_resp = client.get(
        f"{API}/repos/{repo}/git/commits/{commit_sha}",
        headers=headers,
    )
    commit_resp.raise_for_status()
    tree_sha = commit_resp.json()["tree"]["sha"]
    tree_resp = client.get(
        f"{API}/repos/{repo}/git/trees/{tree_sha}",
        headers=headers,
        params={"recursive": "1"},
    )
    tree_resp.raise_for_status()
    tree = tree_resp.json()
    blobs = [x for x in tree.get("tree", []) if x.get("type") == "blob"]
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"files": 0, "bytes": 0, "dates": [], "paths": []}
    )
    file_manifest = []
    for item in blobs:
        path = item["path"]
        cat = category(path)
        date = path_date(path)
        entry = grouped[cat]
        entry["files"] += 1
        entry["bytes"] += int(item.get("size") or 0)
        if date:
            entry["dates"].append(date)
        file_manifest.append({
            "path": path,
            "sha": item.get("sha"),
            "size": item.get("size"),
            "category": cat,
            "path_date": date,
        })
    summary = {}
    for cat, entry in grouped.items():
        dates = sorted(entry["dates"])
        summary[cat] = {
            "files": entry["files"],
            "bytes": entry["bytes"],
            "path_dated_files": len(dates),
            "first_path_date": dates[0] if dates else None,
            "last_path_date": dates[-1] if dates else None,
        }
    return {
        "repository": repo,
        "default_branch": default_branch,
        "commit_sha": commit_sha,
        "tree_sha": tree.get("sha"),
        "truncated": bool(tree.get("truncated")),
        "file_count": len(blobs),
        "total_bytes": sum(int(x.get("size") or 0) for x in blobs),
        "categories": summary,
        "files": file_manifest,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", action="append", dest="repos",
                        help="Repository owner/name; repeat to select. Defaults to known sources.")
    parser.add_argument("--output", default="data/reports/github-source-inventory.json")
    args = parser.parse_args()
    token = os.getenv("GITHUB_TOKEN", "").strip()
    headers = {"User-Agent": "NEPSE-AI-GitHub-Archive-Inventory/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    results = []
    with httpx.Client(timeout=TIMEOUT, headers=headers, follow_redirects=True) as client:
        for repo in (args.repos or DEFAULT_REPOS):
            try:
                results.append(inventory_repo(client, repo))
            except Exception as exc:
                results.append({"repository": repo, "error": f"{type(exc).__name__}: {exc}"})
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "metadata_only_no_download",
        "repositories": results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "repositories": [{
            "repository": x.get("repository"),
            "file_count": x.get("file_count"),
            "total_bytes": x.get("total_bytes"),
            "error": x.get("error"),
        } for x in results],
    }, indent=2))


if __name__ == "__main__":
    main()
