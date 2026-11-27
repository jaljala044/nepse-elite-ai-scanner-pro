"""Import one official NEPSE/SEBON response from a browser HAR archive.

HAR is a transport capture supplied by an operator, not independent proof of
TLS verification, publisher identity, completeness, or source authority. The
importer preserves exact response bytes and keeps all evidence gates closed.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

ALLOWED_HOSTS = {
    "nepalstock.com.np", "www.nepalstock.com.np",
    "sebon.gov.np", "www.sebon.gov.np",
}
DEFAULT_MAX_BYTES = 50 * 1024 * 1024
HARD_MAX_BYTES = 250 * 1024 * 1024


def _official_https_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname in ALLOWED_HOSTS
            and parsed.port in (None, 443)
            and parsed.username is None
            and parsed.password is None
        )
    except (TypeError, ValueError):
        return False


def _has_sensitive_query(url: str) -> bool:
    try:
        parsed = urlparse(url)
        sensitive = {"token", "access_token", "auth", "authorization", "api_key", "apikey", "key", "signature", "sig", "session", "sessionid"}
        return any(name.lower() in sensitive for name, _ in parse_qsl(parsed.query, keep_blank_values=True))
    except (TypeError, ValueError):
        return True


def _header(headers: list, name: str) -> str:
    values = [
        str(item.get("value", ""))
        for item in headers
        if isinstance(item, dict) and str(item.get("name", "")).lower() == name.lower()
    ]
    return values[-1] if values else ""


def _safe_source_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value):
        raise ValueError("source_id must be a 1-64 character filename-safe identifier")
    return value


def capture_har_entry(
    har_path: str | Path,
    entry_index: int,
    source_id: str,
    output_dir: str | Path,
    max_response_bytes: int = DEFAULT_MAX_BYTES,
) -> dict:
    """Extract and immutably store one selected HAR response; never attest TLS."""
    source_id = _safe_source_id(source_id)
    if not isinstance(entry_index, int) or isinstance(entry_index, bool) or entry_index < 0:
        raise ValueError("entry_index must be a non-negative integer")
    if not isinstance(max_response_bytes, int) or isinstance(max_response_bytes, bool) or not 1 <= max_response_bytes <= HARD_MAX_BYTES:
        raise ValueError("max_response_bytes must be between 1 byte and 250 MiB")

    har_file = Path(har_path)
    har_raw = har_file.read_bytes()
    if not har_raw:
        raise ValueError("HAR file is empty")
    har_sha256 = hashlib.sha256(har_raw).hexdigest()
    try:
        archive = json.loads(har_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("HAR file is not valid UTF-8 JSON") from exc
    if not isinstance(archive, dict) or not isinstance(archive.get("log"), dict):
        raise ValueError("HAR must contain a log object")
    entries = archive["log"].get("entries")
    if not isinstance(entries, list) or entry_index >= len(entries):
        raise ValueError("HAR entry_index is outside the captured entries")
    entry = entries[entry_index]
    if not isinstance(entry, dict):
        raise ValueError("selected HAR entry must be an object")

    request = entry.get("request")
    response = entry.get("response")
    if not isinstance(request, dict) or not isinstance(response, dict):
        raise ValueError("selected HAR entry must contain request and response objects")
    request_url = request.get("url")
    response_status = response.get("status")
    if not _official_https_url(request_url):
        raise ValueError("HAR request URL must be HTTPS on an approved official NEPSE or SEBON host")
    if _has_sensitive_query(request_url):
        raise ValueError("HAR request URL contains a credential-like query parameter; sanitize the capture first")
    if not isinstance(response_status, int) or isinstance(response_status, bool) or response_status != 200:
        raise ValueError("selected HAR response must have HTTP status 200")
    response_url = entry.get("response", {}).get("redirectURL") or request_url
    if not _official_https_url(response_url):
        raise ValueError("HAR response URL must be HTTPS on an approved official host")
    if _has_sensitive_query(response_url):
        raise ValueError("HAR response URL contains a credential-like query parameter; sanitize the capture first")

    content = response.get("content")
    if not isinstance(content, dict) or not isinstance(content.get("text"), str):
        raise ValueError("HAR response body is missing; export response content in the HAR")
    try:
        if str(content.get("encoding", "")).lower() == "base64":
            raw = base64.b64decode(content["text"], validate=True)
        else:
            raw = content["text"].encode("utf-8")
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError("HAR response body encoding is invalid") from exc
    if not raw:
        raise ValueError("HAR response body is empty")
    if len(raw) > max_response_bytes:
        raise ValueError("HAR response exceeds max_response_bytes")

    headers = response.get("headers", [])
    if not isinstance(headers, list):
        raise ValueError("HAR response headers must be an array")
    content_type = _header(headers, "content-type").split(";", 1)[0].strip().lower()
    if not content_type:
        raise ValueError("HAR response is missing Content-Type")
    if "json" in content_type:
        try:
            parsed = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("HAR JSON response body is invalid") from exc
        if not isinstance(parsed, (dict, list)):
            raise ValueError("HAR JSON root must be an object or array")
        extension = "json"
        root_type = "array" if isinstance(parsed, list) else "object"
    elif content_type == "application/pdf" or content_type.endswith("/pdf"):
        if not raw.startswith(b"%PDF-"):
            raise ValueError("HAR PDF response does not have a PDF signature")
        extension = "pdf"
        root_type = None
    else:
        raise ValueError("HAR response content type must be JSON or PDF")

    digest = hashlib.sha256(raw).hexdigest()
    retrieved = entry.get("startedDateTime")
    if not isinstance(retrieved, str) or not retrieved.strip():
        retrieved = None
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    raw_path = root / f"{source_id}-{digest}.{extension}"
    if raw_path.exists() and raw_path.read_bytes() != raw:
        raise RuntimeError("content-addressed HAR response path contains different bytes")
    if not raw_path.exists():
        raw_path.write_bytes(raw)



    metadata = {
        "source_id": source_id,
        "capture_method": "operator_supplied_browser_har",
        "request_method": str(request.get("method", "")).upper() or None,
        "url": request_url,
        "response_url": response_url,
        "retrieved_at_utc_from_har": retrieved,
        "http_status": response_status,
        "content_type": content_type,
        "raw_byte_count": len(raw),
        "raw_payload_sha256": digest,
        "raw_payload_path": str(raw_path),
        "har_sha256": har_sha256,
        "json_root_type": root_type,
        "tls_verification_status": "not_attested_by_har",
        "hostname_verification_status": "not_attested_by_har",
        "publisher_authentication_status": "requires_independent_review",
        "source_schema_status": "unreviewed",
        "source_completeness_status": "unknown",
        "manifest_verified": False,
        "membership_admission_allowed": False,
        "production_sector_signals_allowed": False,
    }
    metadata_path = root / f"{source_id}-{digest}.capture.json"
    encoded = json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"
    if metadata_path.exists() and metadata_path.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("content-addressed HAR metadata conflicts with existing file")
    metadata_path.write_text(encoded, encoding="utf-8")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--har", required=True, type=Path)
    parser.add_argument("--entry-index", required=True, type=int)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/evidence/registry"))
    parser.add_argument("--max-response-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args()
    result = capture_har_entry(args.har, args.entry_index, args.source_id,
                               args.output_dir, args.max_response_bytes)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
