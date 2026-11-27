"""Evidence-only capture wrapper for candidate NEPSE index-history HAR routes.

The routes are third-party-discovered candidates, not an official contract.
This module preserves safe request/response evidence but never validates
endpoint authority, TLS, finality, completeness, or promotion eligibility.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

from capture_official_har import capture_har_entry

MAX_REQUEST_BYTES = 2 * 1024 * 1024
SENSITIVE_KEYS = {
    "token", "access_token", "auth", "authorization", "api_key", "apikey",
    "key", "signature", "sig", "session", "sessionid", "password", "secret",
}


def _candidate_route(method: str, url: str) -> dict:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    graph = re.fullmatch(r"/api/nots/graph/index/(\d+)", path)
    history = re.fullmatch(r"/index/history/(\d+)", path)
    if graph and method == "POST":
        family, match = "candidate_graph_post", graph
    elif history and method == "GET":
        family, match = "candidate_index_history_get", history
    else:
        raise ValueError("request does not match a documented candidate NEPSE index route")
    index_id = int(match.group(1))
    return {
        "route_family": family,
        "index_id": index_id,
        "candidate_id_range_match": 51 <= index_id <= 67,
        "route_contract_status": "third_party_discovery_only",
    }


def _contains_sensitive_key(value) -> bool:
    if isinstance(value, dict):
        return any(str(key).lower() in SENSITIVE_KEYS or _contains_sensitive_key(item)
                   for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def capture_index_har_entry(
    har_path: str | Path,
    entry_index: int,
    source_id: str,
    output_dir: str | Path,
) -> dict:
    har_raw = Path(har_path).read_bytes()
    try:
        archive = json.loads(har_raw)
        entry = archive["log"]["entries"][entry_index]
        request = entry["request"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise ValueError("invalid HAR or selected entry") from exc

    method = str(request.get("method", "")).upper()
    url = request.get("url")
    route = _candidate_route(method, url)
    parsed_url = urlparse(url)
    query = parse_qsl(parsed_url.query, keep_blank_values=True)
    if any(key.lower() in SENSITIVE_KEYS for key, _ in query):
        raise ValueError("request query contains a credential-like parameter")

    post_data = request.get("postData")
    request_body_path = None
    request_body_sha256 = None
    request_body_bytes = 0
    request_body_fields = []
    if post_data is not None:
        if not isinstance(post_data, dict) or not isinstance(post_data.get("text"), str):
            raise ValueError("request body must be text JSON when present")
        request_body = post_data["text"].encode("utf-8")
        if len(request_body) > MAX_REQUEST_BYTES:
            raise ValueError("request body exceeds 2 MiB")
        try:
            parsed_body = json.loads(request_body)
        except json.JSONDecodeError as exc:
            raise ValueError("candidate graph request body must be valid JSON") from exc
        if _contains_sensitive_key(parsed_body):
            raise ValueError("request body contains credential-like fields; do not import it")
        request_body_sha256 = hashlib.sha256(request_body).hexdigest()
        request_body_bytes = len(request_body)
        if isinstance(parsed_body, dict):
            request_body_fields = sorted(str(key) for key in parsed_body)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        body_path = out / f"{source_id}-{request_body_sha256}.request.json"
        if body_path.exists() and body_path.read_bytes() != request_body:
            raise RuntimeError("content-addressed request body path conflict")
        if not body_path.exists():
            body_path.write_bytes(request_body)
        request_body_path = str(body_path)
    elif method == "POST":
        raise ValueError("candidate graph POST request body is missing")

    response_metadata = capture_har_entry(
        har_path, entry_index, source_id, output_dir
    )
    result = dict(response_metadata)
    result.update(route)
    result.update({
        "request_path": parsed_url.path,
        "request_query_parameters": [{"name": key, "value": value} for key, value in query],
        "request_body_byte_count": request_body_bytes,
        "request_body_sha256": request_body_sha256,
        "request_body_path": request_body_path,
        "request_body_top_level_fields": request_body_fields,
        "request_safe_headers": {
            "accept": next((h.get("value") for h in request.get("headers", [])
                            if str(h.get("name", "")).lower() == "accept"), None),
            "content_type": next((h.get("value") for h in request.get("headers", [])
                                  if str(h.get("name", "")).lower() == "content-type"), None),
        },
        "request_sensitive_header_names_redacted": sorted({
            str(h.get("name", "")).lower()
            for h in request.get("headers", [])
            if isinstance(h, dict) and str(h.get("name", "")).lower()
            in {"authorization", "cookie", "set-cookie", "x-api-key"}
        }),
        "source_contract_verified": False,
        "history_completeness_verified": False,
        "exchange_calendar_reconciled": False,
        "evidence_gate_passed": False,
        "promotion_allowed": False,
        "production_index_signals_allowed": False,
    })
    sidecar = Path(response_metadata["raw_payload_path"]).with_suffix(".index-capture.json")
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if sidecar.exists() and sidecar.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("index capture metadata conflicts with existing sidecar")
    sidecar.write_text(encoded, encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--har", required=True, type=Path)
    parser.add_argument("--entry-index", required=True, type=int)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/evidence/index"))
    args = parser.parse_args()
    print(json.dumps(capture_index_har_entry(
        args.har, args.entry_index, args.source_id, args.output_dir
    ), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
