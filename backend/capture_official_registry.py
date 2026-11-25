#!/usr/bin/env python3
"""Capture an official NEPSE/SEBON JSON registry response without trusting its schema.

The adapter preserves response bytes and metadata. It does not normalize or
promote records; the captured response must be reviewed before validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ALLOWED_HOSTS = {"nepalstock.com.np", "www.nepalstock.com.np", "sebon.gov.np", "www.sebon.gov.np"}


def capture_registry(url: str, source_id: str, output_dir: str | Path, timeout: int = 30,
                     max_response_bytes: int = 50 * 1024 * 1024) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("registry URL must use HTTPS on an approved official NEPSE or SEBON host")
    if not isinstance(source_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", source_id):
        raise ValueError("source_id must be a 1-64 character filename-safe identifier")
    if timeout < 1 or timeout > 120:
        raise ValueError("timeout must be between 1 and 120 seconds")
    if not isinstance(max_response_bytes, int) or max_response_bytes < 1 or max_response_bytes > 250 * 1024 * 1024:
        raise ValueError("max_response_bytes must be between 1 byte and 250 MiB")
    request = Request(url, headers={"User-Agent": "NEPSE-AI-Registry-Capture/1.0", "Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        if status != 200:
            raise RuntimeError(f"official registry request returned HTTP {status}")
        headers = dict(response.headers.items())
        content_length = headers.get("Content-Length") or headers.get("content-length")
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except (TypeError, ValueError) as exc:
                raise ValueError("registry response has invalid Content-Length") from exc
            if declared_length < 0 or declared_length > max_response_bytes:
                raise ValueError("registry response exceeds max_response_bytes")
        raw = response.read(max_response_bytes + 1)
        if len(raw) > max_response_bytes:
            raise ValueError("registry response exceeds max_response_bytes")
        final_url = response.geturl()
    final = urlparse(final_url)
    if final.scheme != "https" or final.hostname not in ALLOWED_HOSTS:
        raise ValueError("registry redirect target is not an approved official HTTPS host")
    if not raw:
        raise ValueError("official registry response is empty")
    content_type = (headers.get("Content-Type") or headers.get("content-type") or "").lower()
    if "json" not in content_type:
        raise ValueError("official registry response content type is not JSON")
    try:
        parsed_body = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("official registry response is not valid JSON") from exc
    if not isinstance(parsed_body, (dict, list)):
        raise ValueError("official registry JSON root must be an object or array")
    digest = hashlib.sha256(raw).hexdigest()
    retrieved = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    raw_path = root / f"{source_id}-{digest}.json"
    metadata_path = root / f"{source_id}-{digest}.capture.json"
    if raw_path.exists() and raw_path.read_bytes() != raw:
        raise RuntimeError("content-addressed registry path contains different bytes")
    if not raw_path.exists():
        raw_path.write_bytes(raw)
    metadata = {
        "source_id": source_id, "url": url, "final_url": final_url,
        "retrieved_at_utc": retrieved, "http_status": status,
        "content_type": content_type, "raw_byte_count": len(raw),
        "raw_payload_sha256": digest, "raw_payload_path": str(raw_path),
        "json_root_type": "array" if isinstance(parsed_body, list) else "object",
        "schema_review_status": "unreviewed", "manifest_verified": False,
    }
    encoded = json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"
    if metadata_path.exists() and metadata_path.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("content-addressed registry metadata conflicts with existing file")
    metadata_path.write_text(encoded, encoding="utf-8")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/evidence/registry"))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--max-response-bytes", type=int, default=50 * 1024 * 1024)
    args = parser.parse_args()
    print(json.dumps(capture_registry(args.url, args.source_id, args.output_dir, args.timeout,
                                      args.max_response_bytes),
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
