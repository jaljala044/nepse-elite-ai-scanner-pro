#!/usr/bin/env python3
"""Capture raw NEPSE holiday API bytes using the public NEPSE client flow.

No user credentials are used. The raw response is preserved before parsing.
Authentication tokens and token-endpoint responses are never written to disk.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from nepse_client import NepseClient


def capture(year: int, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    captured: dict = {}
    client = NepseClient(timeout=45.0)

    def save_holiday_response(response) -> None:
        path = urlparse(str(response.url)).path
        if path != "/api/nots/holiday/list":
            return
        captured["body"] = response.content
        captured["status"] = response.status_code
        captured["url"] = str(response.url)
        captured["headers"] = {
            key: response.headers.get(key)
            for key in ("date", "content-type", "content-length", "server")
            if response.headers.get(key) is not None
        }

    client.client.event_hooks["response"].append(save_holiday_response)
    error = None
    result = None
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = client.getHolidayList(year=year)
    except Exception as exc:  # preserve only safe exception metadata
        error = {"type": type(exc).__name__, "message": str(exc)[:300]}
    finally:
        client.close()

    report = {
        "source_id": "NEPSE_OFFICIAL_HOLIDAY_API",
        "source_url": captured.get("url", f"https://nepalstock.com.np/api/nots/holiday/list?year={year}"),
        "requested_year": year,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "http_status": captured.get("status"),
        "response_headers": captured.get("headers", {}),
        "response_bytes": len(captured.get("body", b"")),
        "response_sha256": None,
        "response_preserved": bool(captured.get("body")),
        "parsed_record_count": len(result) if isinstance(result, list) else None,
        "request_error": error,
        "calendar_claims_promoted": False,
        "policy": "raw_source_capture_only_no_calendar_promotion",
    }

    if captured.get("body") is not None:
        body = captured["body"]
        report["response_sha256"] = hashlib.sha256(body).hexdigest()
        (output_dir / "response-body.bin").write_bytes(body)
        try:
            parsed = json.loads(body)
            (output_dir / "parsed-response.json").write_text(
                json.dumps(parsed, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            report["json_shape"] = type(parsed).__name__
        except Exception as exc:
            report["json_parse_error"] = type(exc).__name__
        (output_dir / "response-headers.json").write_text(
            json.dumps(captured.get("headers", {}), indent=2) + "\n",
            encoding="utf-8",
        )
        (output_dir / "source-url.txt").write_text(captured["url"] + "\n", encoding="utf-8")
        (output_dir / "SHA256SUMS").write_text(
            f"{report['response_sha256']}  response-body.bin\n",
            encoding="utf-8",
        )

    (output_dir / "capture-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    report = capture(args.year, args.output_dir)
    print(json.dumps({
        "http_status": report["http_status"],
        "response_bytes": report["response_bytes"],
        "response_sha256": report["response_sha256"],
        "parsed_record_count": report["parsed_record_count"],
        "response_preserved": report["response_preserved"],
        "request_error": report["request_error"],
        "calendar_claims_promoted": False,
    }, indent=2))
    return 0 if report["http_status"] == 200 and report["response_preserved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
