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
    ],
}

GITHUB_REPOS = {
    "jaljala_history_starter": "jaljala044/nepse-history-starter",
    "jaljala_smc_data": "jaljala044/nepse-smc-data",
    "samirwagle_archive": "SamirWagle/Nepse-All-Scraper",
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
                if label == "samirwagle_archive":
                    wanted = (
                        lower == "data/company_list.json"
                        or (lower.startswith("data/indices/") and lower.endswith(".csv"))
                        or (lower.startswith("data/floorsheet/") and lower.endswith((".csv", ".json")))
                    )
                else:
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
            if label == "samirwagle_archive":
                floor_files = sorted((p, s) for p, s in candidates if "data/floorsheet/" in p)
                keep = {p for p, _ in floor_files[-10:]}
                candidates = [(p, s) for p, s in candidates
                              if "data/floorsheet/" not in p or p in keep]
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


def _provider_access_approval(name: str, data_type: str, url: str) -> tuple[bool, str]:
    """Require a reviewed provider contract before any configured-provider request."""
    raw = os.getenv("NEPSE_PROVIDER_ACCESS_MANIFEST", "").strip()
    if not raw:
        return False, "provider_access_manifest_missing"
    try:
        manifest = json.loads(raw)
        entry = manifest.get("providers", {}).get(name)
        if not isinstance(entry, dict):
            return False, "provider_access_approval_missing"
        from datetime import date
        if entry.get("status") != "approved":
            return False, "provider_access_not_approved"
        if data_type not in entry.get("allowed_data_types", []):
            return False, "provider_data_type_not_approved"
        if entry.get("rights_status") not in {"research_only", "internal_use", "redistribution_permitted"}:
            return False, "provider_rights_not_approved"
        required = ("reviewer", "evidence_ref", "contract_ref", "valid_until")
        if not all(isinstance(entry.get(key), str) and entry[key].strip() for key in required):
            return False, "provider_approval_evidence_incomplete"
        if date.fromisoformat(entry["valid_until"]) < date.today():
            return False, "provider_access_approval_expired"
        parsed = httpx.URL(url)
        if parsed.scheme != "https" or parsed.host not in entry.get("allowed_hosts", []):
            return False, "provider_endpoint_host_not_approved"
        prefixes = entry.get("allowed_path_prefixes", [])
        if not any(isinstance(prefix, str) and parsed.path.startswith(prefix) for prefix in prefixes):
            return False, "provider_endpoint_path_not_approved"
        return True, "approved"
    except (ValueError, TypeError, AttributeError):
        return False, "provider_access_manifest_invalid"


def collect_configured_provider(
    client: httpx.Client, name: str, data_type: str, *,
    equities: list[dict] | None = None, session_dates: list[str] | None = None,
    period_start: str | None = None, period_end: str | None = None,
) -> list[dict[str, Any]]:
    """Capture provider-documented per-equity charts or per-session floorsheets.

    URL templates may use only {symbol}, {security_id}, {date}, {from}, {to}.
    A bulk archive URL can be supplied instead. No endpoint/query is invented.
    """
    if data_type not in {"floorsheet", "chart"}:
        raise ValueError("data_type must be floorsheet or chart")
    prefix = re.sub(r"[^A-Z0-9]", "_", name.upper())
    template = os.getenv(f"{prefix}_{data_type.upper()}_URL_TEMPLATE", "").strip()
    bulk_url = os.getenv(f"{prefix}_{data_type.upper()}_DATA_URL", "").strip()
    if not template and not bulk_url:
        return [{"source": name, "data_type": data_type, "status": "BLOCKED_ACCESS",
                 "required": f"{prefix}_{data_type.upper()}_URL_TEMPLATE or {prefix}_{data_type.upper()}_DATA_URL"}]
    token = os.getenv(f"{prefix}_API_TOKEN", "").strip()
    api_key = os.getenv(f"{prefix}_API_KEY", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if api_key:
        headers["X-Api-Key"] = api_key
    targets: list[tuple[str, dict[str, str]]] = []
    if template:
        fields = set(re.findall(r"\{([a-z_]+)\}", template))
        allowed = {"symbol", "security_id", "date", "from", "to"}
        if not fields <= allowed:
            return [{"source": name, "data_type": data_type, "status": "BLOCKED_ACCESS",
                     "error": "unsupported_url_template_placeholder"}]
        permitted_for_type = ({"symbol", "security_id", "from", "to"} if data_type == "chart"
                              else {"date", "symbol", "security_id", "from", "to"})
        if not fields <= permitted_for_type or (data_type == "floorsheet" and "date" in fields and "symbol" in fields):
            return [{"source": name, "data_type": data_type, "status": "BLOCKED_ACCESS",
                     "error": "template_placeholders_conflict_with_data_type"}]
        if data_type == "chart" and "symbol" in fields:
            if not equities:
                return [{"source": name, "data_type": data_type, "status": "BLOCKED_DEPENDENCY",
                         "error": "complete_equity_universe_required_for_per_symbol_chart_capture"}]
            for equity in equities:
                values = {"symbol": str(equity["symbol"]), "security_id": str(equity["security_id"]),
                          "from": period_start or "", "to": period_end or ""}
                targets.append((str(equity["symbol"]), values))
        elif data_type == "floorsheet" and "date" in fields:
            if not session_dates:
                return [{"source": name, "data_type": data_type, "status": "BLOCKED_DEPENDENCY",
                         "error": "exchange_verified_session_calendar_required_for_daily_floorsheet_capture"}]
            for day in session_dates:
                targets.append((day, {"date": day, "from": period_start or "", "to": period_end or ""}))
        elif "symbol" in fields:
            if not equities:
                return [{"source": name, "data_type": data_type, "status": "BLOCKED_DEPENDENCY",
                         "error": "complete_equity_universe_required_for_per_symbol_capture"}]
            for equity in equities:
                targets.append((str(equity["symbol"]), {
                    "symbol": str(equity["symbol"]), "security_id": str(equity["security_id"]),
                    "from": period_start or "", "to": period_end or "",
                }))
        else:
            targets.append(("bulk_archive", {"from": period_start or "", "to": period_end or ""}))
    else:
        targets.append(("bulk_archive", {"from": period_start or "", "to": period_end or ""}))

    records = []
    for label, values in targets:
        try:
            url = template.format(**values) if template else bulk_url
            approved, approval_reason = _provider_access_approval(name, data_type, url)
            if not approved:
                records.append({"source": name, "data_type": data_type, "target": label,
                                "status": "BLOCKED_ACCESS", "url": url,
                                "error": approval_reason})
                continue
            response = client.get(url, headers=headers, follow_redirects=False)
            response.raise_for_status()
            if len(response.content) > 250 * 1024 * 1024:
                raise ValueError("response exceeded 250 MiB safety limit")
            saved = _save(name, f"{data_type}_{label}", response.content, url,
                          response.headers.get("content-type", ""))
            records.append({**saved, "data_type": data_type,
                            "equity_symbol": label if data_type == "chart" or "symbol" in values else None,
                            "session_date": label if data_type == "floorsheet" and "date" in values else None,
                            "status": "PARTIAL_EVIDENCED",
                            "note": "Raw payload captured; parsed coverage and completeness remain to be validated."})
        except Exception as exc:
            records.append({"source": name, "data_type": data_type, "target": label,
                            "status": "BLOCKED_ACCESS", "url": template or bulk_url,
                            "error": f"{type(exc).__name__}: {exc}"})
    return records



def collect_sharesansar_public_chart_archive(
    client: httpx.Client, equities: list[dict] | None,
) -> list[dict[str, Any]]:
    """Capture the documented public ShareSansar-derived per-symbol chart archive."""
    if not equities:
        return [{"source": "sharesansar", "data_type": "chart",
                 "status": "BLOCKED_DEPENDENCY",
                 "required": "complete equity universe with symbol and security_id"}]
    records = []
    base = "https://omitnomis.github.io/ShareSansarScraper/api/history/{symbol}.json"
    for equity in equities:
        symbol = str(equity["symbol"]).strip().upper()
        url = base.format(symbol=symbol)
        try:
            response = client.get(url)
            response.raise_for_status()
            if len(response.content) > 250 * 1024 * 1024:
                raise ValueError("response exceeded 250 MiB safety limit")
            saved = _save("sharesansar", f"chart_history_{symbol}", response.content, url,
                          response.headers.get("content-type", ""))
            records.append({**saved, "data_type": "chart", "equity_symbol": symbol,
                            "security_id": str(equity["security_id"]),
                            "status": "PARTIAL_EVIDENCED",
                            "note": "Public ShareSansar-derived history captured; filter five-year period and validate coverage/fields."})
        except Exception as exc:
            records.append({"source": "sharesansar", "data_type": "chart",
                            "equity_symbol": symbol, "url": url,
                            "status": "BLOCKED_ACCESS",
                            "error": f"{type(exc).__name__}: {exc}"})
    return records


def collect(sources: list[str] | None = None, *, as_of_date: str | None = None,
            equities: list[dict] | None = None,
            session_dates: list[str] | None = None) -> dict[str, Any]:
    from app.historical_market_data_policy import (
        PROVIDERS, REFERENCE_PROVIDERS, DIAGNOSTIC_PROVIDERS,
        build_five_year_collection_plan,
    )
    available = set(SOURCES) | set(GITHUB_REPOS) | set(PROVIDERS) | set(REFERENCE_PROVIDERS) | set(DIAGNOSTIC_PROVIDERS) | {
        "hamroshare", "nepsepy", "nepse_client", "nepse_data_api", "nepse_link"
    }
    selected = set(sources or available)
    unknown = selected - available
    if unknown:
        raise ValueError("Unknown sources: " + ", ".join(sorted(unknown)))
    plan = None
    period_start = period_end = None
    if as_of_date is not None or equities is not None:
        if as_of_date is None or equities is None:
            raise ValueError("as_of_date and complete equities universe must be supplied together")
        plan = build_five_year_collection_plan(as_of_date=as_of_date, equities=equities,
                                               session_dates=session_dates)
        period_start, period_end = plan["period_start"], plan["period_end"]
    if session_dates is not None:
        if not isinstance(session_dates, list) or any(not isinstance(day, str) for day in session_dates):
            raise ValueError("session_dates must be a list of ISO dates")
        from datetime import date
        for day in session_dates:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError("session_dates must be zero-padded ISO dates")
        if len(session_dates) != len(set(session_dates)):
            raise ValueError("session_dates must not contain duplicates")
    records: list[dict[str, Any]] = []
    with httpx.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=False) as client:
        records.extend(collect_public_archives(client, selected))
        records.extend(collect_user_github_repos(client, selected))
        if "sharesansar" in selected:
            records.extend(collect_sharesansar_public_chart_archive(client, equities))
        for name in (*PROVIDERS, *REFERENCE_PROVIDERS, *DIAGNOSTIC_PROVIDERS):
            if name in selected:
                for data_type in ("floorsheet", "chart"):
                    records.extend(collect_configured_provider(
                        client, name, data_type, equities=equities,
                        session_dates=session_dates, period_start=period_start,
                        period_end=period_end))
        for name in ("hamroshare", "nepsepy", "nepse_client", "nepse_data_api", "nepse_link"):
            if name in selected:
                for data_type in ("floorsheet", "chart"):
                    records.extend(collect_configured_provider(
                        client, name, data_type, equities=equities,
                        session_dates=session_dates, period_start=period_start,
                        period_end=period_end))
    manifest = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_five_year_raw_collection",
        "collection_plan": plan,
        "session_calendar_count": len(session_dates or []),
        "records": records,
        "note": "Raw snapshots only; five-year coverage, lineage and two-source matching must pass before COMPLETE_EVIDENCED.",
    }
    manifest_dir = ROOT / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"collection_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path.relative_to(ROOT.parent))
    return manifest
