#!/usr/bin/env python3
"""Probe NEPSE's publicly documented-in-client general notice endpoint.

This probe uses one unauthenticated HTTPS GET with normal TLS certificate
verification. It does not solve challenges, generate tokens, log in, or retry
with alternate identities. If the endpoint requires authentication or blocks
the request, the result is recorded and the probe stops.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

NOTICE_URL = "https://www.nepalstock.com/api/web/notice/"
KEYWORDS = ("holiday", "closed", "closure", "trading", "market", "dashain", "tihar", "chhath", "suspension", "resume")


def summarize_notice_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = None
        for key in ("content", "data", "notices", "result", "items"):
            if isinstance(payload.get(key), list):
                records = payload[key]
                break
        if records is None:
            records = [payload]
    else:
        records = []

    candidates = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        text = json.dumps(record, ensure_ascii=False, sort_keys=True)
        if any(re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", text.lower()) for word in KEYWORDS):
            candidates.append({"record_index": index, "record": record})
    return {
        "top_level_type": type(payload).__name__,
        "record_count": len(records),
        "keyword_candidate_count": len(candidates),
        "keyword_candidates": candidates,
    }


def probe(output_dir: str | Path, timeout: float = 30.0) -> dict[str, Any]:
    if timeout < 5 or timeout > 90:
        raise ValueError("timeout must be between 5 and 90 seconds")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "generated_at_utc": generated,
        "url": NOTICE_URL,
        "method": "GET",
        "authentication": "none",
        "tls_verification": True,
        "redirects_followed": False,
        "status": "not_attempted",
    }
    try:
        with httpx.Client(
            timeout=httpx.Timeout(timeout, connect=min(timeout, 15.0)),
            verify=True,
            follow_redirects=False,
            headers={"Accept": "application/json", "User-Agent": "NEPSE-Historical-Audit/1.0"},
        ) as client:
            response = client.get(NOTICE_URL)
        body = response.content
        digest = hashlib.sha256(body).hexdigest()
        raw_path = output / "nepse-public-notices-response.bin"
        raw_path.write_bytes(body)
        report.update({
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "content_length_bytes": len(body),
            "response_sha256": digest,
            "raw_response_path": str(raw_path),
            "response_url": str(response.url),
        })
        if response.status_code != 200:
            report["status"] = "endpoint_not_publicly_readable_without_auth"
        else:
            try:
                payload = response.json()
            except ValueError:
                report["status"] = "http_200_non_json_response"
                report["body_preview"] = body[:500].decode("utf-8", errors="replace")
            else:
                report["status"] = "public_json_response"
                report["payload_summary"] = summarize_notice_payload(payload)
                json_path = output / "nepse-public-notices-response.json"
                json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                report["parsed_response_path"] = str(json_path)
    except Exception as exc:
        report.update({
            "status": "request_error",
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
    report_path = output / "nepse-public-notices-probe.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/reports/nepse-public-notices"))
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    report = probe(args.output_dir, args.timeout)
    print(json.dumps({
        "status": report["status"],
        "http_status": report.get("http_status"),
        "content_type": report.get("content_type"),
        "content_length_bytes": report.get("content_length_bytes"),
        "response_sha256": report.get("response_sha256"),
        "keyword_candidate_count": (report.get("payload_summary") or {}).get("keyword_candidate_count"),
        "error_type": report.get("error_type"),
    }, indent=2))


if __name__ == "__main__":
    main()
