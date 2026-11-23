"""Read-only source collectors. Raw payloads are preserved with hashes and provenance.

No credentials are hard-coded. Optional paid/private feeds must be configured using
environment variables and only through documented, provider-authorized endpoints.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2] / "data" / "raw"
TIMEOUT = httpx.Timeout(25.0, connect=10.0)
HEADERS = {"User-Agent": "NEPSE-ELITE-AI-SCANNER/0.2 (read-only research collector)"}

SOURCES: dict[str, list[str]] = {
    "sharesansar_archive": [
        "https://omitnomis.github.io/ShareSansarScraper/api/meta.json",
        "https://omitnomis.github.io/ShareSansarScraper/api/symbols.json",
        "https://omitnomis.github.io/ShareSansarScraper/api/latest.json",
        "https://omitnomis.github.io/ShareSansarScraper/api/recap/latest.json",
    ],
    "samirwagle_archive": [
        "https://samirwagle.github.io/Nepse-All-Scraper/docs/api/status.json",
        "https://samirwagle.github.io/Nepse-All-Scraper/docs/api/latest.json",
        "https://samirwagle.github.io/Nepse-All-Scraper/docs/api/companies.json",
        "https://samirwagle.github.io/Nepse-All-Scraper/docs/api/floorsheet/index.json",
    ],
}

GITHUB_REPOS = {
    "jaljala_history_starter": "jaljala044/nepse-history-starter",
    "jaljala_smc_data": "jaljala044/nepse-smc-data",
}
GITHUB_API = "https://api.github.com"


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")[:160] or "payload"


def _save(source: str, label: str, content: bytes, url: str, content_type: str = "") -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    folder = ROOT / _safe_name(source) / now.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(content).hexdigest()
    path = folder / f"{now.strftime('%H%M%S')}_{_safe_name(label)}_{digest[:12]}.bin"
    path.write_bytes(content)
    return {
        "source": source, "label": label, "url": url,
        "retrieved_at_utc": now.isoformat(), "sha256": digest,
        "bytes": len(content), "content_type": content_type,
        "path": str(path.relative_to(ROOT.parent)),
    }


def collect_public_archives(client: httpx.Client, selected: set[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source, urls in SOURCES.items():
        if source not in selected:
            continue
        for url in urls:
            label = url.rsplit("/", 1)[-1]
            try:
                response = client.get(url)
                response.raise_for_status()
                if len(response.content) > 30 * 1024 * 1024:
                    raise ValueError("response exceeded 30 MiB safety limit")
                records.append(_save(source, label, response.content, url,
                                     response.headers.get("content-type", "")))
            except Exception as exc:
                records.append({"source": source, "label": label, "url": url,
                                "error": f"{type(exc).__name__}: {exc}"} )
    return records


def collect_user_github_repos(client: httpx.Client, selected: set[str]) -> list[dict[str, Any]]:
    """Download selected data artifacts from the user's public repositories.

    The collector preserves raw files. It does not assume their schema or merge them
    into normalized OHLCV until a separate validator has inspected each format.
    """
    records: list[dict[str, Any]] = []
    for label, repo in GITHUB_REPOS.items():
        if label not in selected:
            continue
        tree_url = f"{GITHUB_API}/repos/{repo}/git/trees/main?recursive=1"
        try:
            response = client.get(tree_url, headers={"Accept": "application/vnd.github+json"})
            response.raise_for_status()
            tree = response.json().get("tree", [])
            candidates = []
            for item in tree:
                path = item.get("path", "")
                if item.get("type") != "blob":
                    continue
                lower = path.lower()
                wanted = (
                    lower.endswith((".csv", ".json", ".txt", ".xlsx", ".parquet"))
                    and (
                        "scanner_inputs/" in lower
                        or "historical_imports/" in lower
                        or "03_stock_charts_ohlcv/" in lower
                        or "02_floorsheet_daily/" in lower
                        or "01_market_indices/" in lower
                        or "00_daily_eod_prices/" in lower
                        or lower in {
                            "ai_upload_package.txt",
                            "nepse_final_capital_safe_setups.csv",
                            "nepse_kheladi_20d_floorsheet_intel.csv",
                            "intraday_buy_alerts.txt",
                        }
                    )
                )
                if wanted and int(item.get("size", 0)) <= 30 * 1024 * 1024:
                    candidates.append((path, item.get("size", 0)))
            for path, size in candidates:
                raw_url = f"https://raw.githubusercontent.com/{repo}/main/{path}"
                try:
                    file_response = client.get(raw_url)
                    file_response.raise_for_status()
                    if len(file_response.content) > 30 * 1024 * 1024:
                        raise ValueError("file exceeded 30 MiB safety limit")
                    records.append(_save(label, path, file_response.content, raw_url,
                                          file_response.headers.get("content-type", "")))
                except Exception as exc:
                    records.append({"source": label, "label": path, "url": raw_url,
                                    "error": f"{type(exc).__name__}: {exc}"})
        except Exception as exc:
            records.append({"source": label, "url": tree_url,
                            "error": f"{type(exc).__name__}: {exc}"})
    return records


def collect_configured_provider(client: httpx.Client, name: str) -> dict[str, Any]:
    """Fetch a provider's documented JSON endpoint only when explicitly configured.

    Set <NAME>_DATA_URL to the exact endpoint supplied by the provider. If needed,
    set <NAME>_API_TOKEN. This intentionally does not guess undocumented app APIs.
    """
    prefix = re.sub(r"[^A-Z0-9]", "_", name.upper())
    url = os.getenv(f"{prefix}_DATA_URL", "").strip()
    if not url:
        return {"source": name, "status": "not_configured",
                "required": f"{prefix}_DATA_URL (provider-documented endpoint)"}
    headers = {}
    token = os.getenv(f"{prefix}_API_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        if len(response.content) > 30 * 1024 * 1024:
            raise ValueError("response exceeded 30 MiB safety limit")
        return _save(name, "provider_payload", response.content, url,
                     response.headers.get("content-type", ""))
    except Exception as exc:
        return {"source": name, "url": url, "error": f"{type(exc).__name__}: {exc}"}


def collect(sources: list[str] | None = None) -> dict[str, Any]:
    available = set(SOURCES) | set(GITHUB_REPOS) | {
        "chukul", "sharehub", "hamroshare", "nepsealpha"
    }
    selected = set(sources or available)
    unknown = selected - available
    if unknown:
        raise ValueError("Unknown sources: " + ", ".join(sorted(unknown)))
    records: list[dict[str, Any]] = []
    with httpx.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
        records.extend(collect_public_archives(client, selected))
        records.extend(collect_user_github_repos(client, selected))
        for name in ("chukul", "sharehub", "hamroshare", "nepsealpha"):
            if name in selected:
                records.append(collect_configured_provider(client, name))
    manifest = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_raw_collection",
        "records": records,
        "note": "Raw snapshots only; no source is considered authoritative until reconciled."
    }
    manifest_dir = ROOT / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"collection_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path.relative_to(ROOT.parent))
    return manifest
