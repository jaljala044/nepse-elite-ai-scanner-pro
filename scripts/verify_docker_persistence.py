#!/usr/bin/env python3
"""Disposable Docker-volume persistence drill for the NEPSE API.

Run from the repository root against a disposable Compose deployment. This
writes one synthetic symbol and intentionally does not delete the imported row.
Do not run against a production database.
"""
from __future__ import annotations

import json
import secrets
import subprocess
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
SYMBOL = "P4" + secrets.token_hex(4).upper()
CSV = (
    "symbol,date,open,high,low,close,volume\n"
    f"{SYMBOL},2025-01-02,100,105,99,103,1234\n"
)


def request(path: str, *, method: str = "GET", data: bytes | None = None,
            headers: dict[str, str] | None = None):
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_healthy(timeout_seconds: int = 60) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = "health endpoint did not become ready"
    while time.monotonic() < deadline:
        try:
            if request("/health").get("status") == "ok":
                return
        except Exception as exc:  # service may be restarting
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(f"API failed to become healthy: {last_error}")


def get_expected_row() -> dict:
    payload = request(f"/v1/data/{SYMBOL}")
    rows = payload.get("rows", [])
    if len(rows) != 1:
        raise AssertionError(f"expected exactly one stored row, got {len(rows)}")
    row = rows[0]
    expected = {
        "date": "2025-01-02", "open": 100.0, "high": 105.0,
        "low": 99.0, "close": 103.0, "volume": 1234,
    }
    normalized = dict(row)
    normalized["date"] = str(normalized.get("date", ""))[:10]
    if normalized != expected:
        raise AssertionError(f"stored row differs: {normalized!r}")
    return normalized


def main() -> None:
    subprocess.run(["docker", "compose", "config", "--quiet"], check=True)
    wait_healthy()

    boundary = "----nepse-p428-" + secrets.token_hex(12)
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="persistence-smoke.csv"\r\n'
        "Content-Type: text/csv\r\n\r\n"
        f"{CSV}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    imported = request(
        "/v1/ingest/csv", method="POST", data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Source-Label": "p4_29_synthetic_persistence_smoke",
        },
    )
    if imported.get("rows_accepted") != 1 or SYMBOL not in imported.get("symbols", []):
        raise AssertionError(f"unexpected ingest response: {imported!r}")

    before = get_expected_row()
    subprocess.run(["docker", "compose", "restart", "nepse-api"], check=True)
    wait_healthy()
    after = get_expected_row()
    if before != after:
        raise AssertionError("stored row changed after container restart")

    print(json.dumps({
        "status": "restart_persistence_passed",
        "symbol": SYMBOL,
        "batch_id": imported.get("batch_id"),
        "rows_accepted": imported.get("rows_accepted"),
        "row_before_restart": before,
        "row_after_restart": after,
        "production_eligible": False,
        "note": "Synthetic single-container restart test only; not a host-loss or cloud durability test.",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
