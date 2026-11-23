"""Download the identified public Kaggle NEPSE floorsheet dataset to local staging.

Requires the Kaggle CLI to be installed and configured by the account owner.
No Kaggle token is read, uploaded, printed, or committed by this script.
Raw downloaded data is not pushed to GitHub automatically.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

DATASET = "qramkrishna/nepal-stock-exchange-data"
REPO_ROOT = Path(__file__).resolve().parents[1]
STAGING = REPO_ROOT / "data" / "raw" / "kaggle"
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 5 * 1024 * 1024 * 1024
MAX_MEMBER_BYTES = 512 * 1024 * 1024
MAX_FILES = 2500

def safe_member_path(name: str) -> Path:
    pure = PurePosixPath(name)
    if pure.is_absolute() or not pure.parts or any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError(f"Unsafe archive member path: {name!r}")
    return Path(*pure.parts)

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def inspect_csv(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
            sample = []
            for _, row in zip(range(3), reader):
                sample.append(row)
        return {"header": header, "sample_rows": len(sample)}
    except Exception as exc:
        return {"inspection_error": f"{type(exc).__name__}: {exc}"}

def run() -> int:
    parser = argparse.ArgumentParser(description="Download Kaggle NEPSE historical floorsheet into local staging")
    parser.add_argument("--confirm-download", action="store_true",
                        help="Required flag to download the dataset")
    args = parser.parse_args()
    if not args.confirm_download:
        parser.error("Add --confirm-download to explicitly start the Kaggle download")
    if shutil.which("kaggle") is None:
        print("Kaggle CLI not found. Install it and configure your Kaggle account locally.", file=sys.stderr)
        return 2

    STAGING.mkdir(parents=True, exist_ok=True)
    work = STAGING / "download"
    work.mkdir(parents=True, exist_ok=True)
    command = ["kaggle", "datasets", "download", "-d", DATASET, "-p", str(work)]
    print("Downloading dataset:", DATASET)
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        print("Kaggle CLI download failed. Check your local Kaggle access and dataset terms.", file=sys.stderr)
        return completed.returncode

    archives = sorted(work.glob("*.zip"))
    if not archives:
        print("Kaggle CLI completed but did not produce a ZIP archive.", file=sys.stderr)
        return 3

    archive = archives[-1]
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        print(f"Archive exceeds {MAX_ARCHIVE_BYTES} byte safety limit.", file=sys.stderr)
        return 4

    output = STAGING / "qramkrishna_nepal_stock_exchange_data"
    output.mkdir(parents=True, exist_ok=True)
    files = []
    total_size = 0
    with zipfile.ZipFile(archive) as bundle:
        members = [m for m in bundle.infolist() if not m.is_dir()]
        if len(members) > MAX_FILES:
            raise ValueError(f"Archive has too many files: {len(members)}")
        for member in members:
            relative = safe_member_path(member.filename)
            if member.file_size > MAX_MEMBER_BYTES:
                raise ValueError(f"Archive member exceeds size limit: {member.filename}")
            total_size += member.file_size
            if total_size > MAX_TOTAL_UNCOMPRESSED:
                raise ValueError("Archive exceeds total uncompressed size limit")
            if relative.suffix.lower() not in (".csv", ".txt", ".json"):
                continue
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as src, destination.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            record = {
                "path": str(destination.relative_to(REPO_ROOT)),
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "format": relative.suffix.lower(),
            }
            if relative.suffix.lower() == ".csv":
                record.update(inspect_csv(destination))
            files.append(record)

    manifest = {
        "dataset": DATASET,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive_sha256": sha256_file(archive),
        "archive_bytes": archive.stat().st_size,
        "files_extracted": len(files),
        "files": files,
        "coverage_note": "The dataset listing describes historical floorsheet records through 2019-10-10. Validate actual per-file dates before combining with other sources.",
        "status": "raw_staged_schema_inspection_required",
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({
        "dataset": DATASET, "files_extracted": len(files),
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "note": "Files are local staging only; not committed to GitHub."
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(run())
