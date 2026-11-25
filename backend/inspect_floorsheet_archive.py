#!/usr/bin/env python3
"""Create a bounded, non-extracting inventory of a floorsheet ZIP archive.

Only the ZIP central directory is inspected. No member is decompressed or
written to disk. The report pins the archive SHA-256 and lists per-member
metadata so large user archives can be reviewed before any parsing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import stat
from datetime import date
import zipfile
from pathlib import Path, PurePosixPath

DEFAULT_MAX_ENTRIES = 200_000
DEFAULT_MAX_TOTAL_UNCOMPRESSED = 20 * 1024**3
DEFAULT_MAX_MEMBER_UNCOMPRESSED = 2 * 1024**3
DEFAULT_MAX_COMPRESSION_RATIO = 1_000.0


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _member_path_issue(name: str) -> str | None:
    if not isinstance(name, str) or not name:
        return "empty_member_name"
    if "\\" in name:
        return "backslash_in_member_name"
    if name.startswith("/") or name.startswith("//"):
        return "absolute_member_path"
    path = PurePosixPath(name)
    if any(part in ("..", "") for part in path.parts):
        return "path_traversal_or_empty_component"
    if path.parts and ":" in path.parts[0]:
        return "drive_or_uri_member_path"
    return None


def inspect_zip(
    archive_path: str | Path,
    *,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    max_total_uncompressed: int = DEFAULT_MAX_TOTAL_UNCOMPRESSED,
    max_member_uncompressed: int = DEFAULT_MAX_MEMBER_UNCOMPRESSED,
    max_compression_ratio: float = DEFAULT_MAX_COMPRESSION_RATIO,
) -> dict:
    path = Path(archive_path)
    if not path.is_file():
        raise ValueError("archive_path must identify an existing regular file")
    for name, value in (
        ("max_entries", max_entries),
        ("max_total_uncompressed", max_total_uncompressed),
        ("max_member_uncompressed", max_member_uncompressed),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if (
        not isinstance(max_compression_ratio, (int, float))
        or isinstance(max_compression_ratio, bool)
        or not math.isfinite(max_compression_ratio)
        or max_compression_ratio <= 0
    ):
        raise ValueError("max_compression_ratio must be finite and positive")

    before_stat = path.stat()
    archive_hash = sha256_file(path)
    entries = []
    issues = []
    seen_names = set()
    seen_casefold = {}
    total_uncompressed = 0
    total_compressed = 0
    extension_counts = {}
    filename_dates = {}
    filename_date_errors = []

    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            if len(infos) > max_entries:
                issues.append({
                    "code": "entry_count_limit_exceeded",
                    "observed": len(infos), "limit": max_entries,
                })
            for info in infos:
                name = info.filename
                member_issues = []
                path_issue = _member_path_issue(name)
                if path_issue:
                    member_issues.append(path_issue)
                if name in seen_names:
                    member_issues.append("duplicate_member_name")
                seen_names.add(name)
                folded = name.casefold()
                prior_casefold = seen_casefold.get(folded)
                if prior_casefold is not None and prior_casefold != name:
                    member_issues.append("casefold_name_collision")
                else:
                    seen_casefold[folded] = name

                unix_mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(unix_mode):
                    member_issues.append("symbolic_link_member")
                if info.flag_bits & 0x1:
                    member_issues.append("encrypted_member")
                if info.file_size < 0 or info.compress_size < 0:
                    member_issues.append("negative_size_metadata")
                if info.file_size > max_member_uncompressed:
                    member_issues.append("member_size_limit_exceeded")
                total_uncompressed += max(info.file_size, 0)
                total_compressed += max(info.compress_size, 0)
                if not info.is_dir():
                    suffix = Path(name).suffix.lower() or "[no_extension]"
                    extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
                    match = re.search(r"(?<!\d)(20\d{2})[-_]?([01]\d)[-_]?([0-3]\d)(?!\d)", name)
                    if match:
                        candidate = "-".join(match.groups())
                        try:
                            date.fromisoformat(candidate)
                            filename_dates.setdefault(candidate, []).append(name)
                        except ValueError:
                            filename_date_errors.append({"member": name, "candidate": candidate})
                ratio = (
                    float("inf") if info.file_size > 0 and info.compress_size == 0
                    else (info.file_size / info.compress_size if info.compress_size else 0.0)
                )
                if ratio > max_compression_ratio:
                    member_issues.append("compression_ratio_limit_exceeded")

                entry = {
                    "name": name,
                    "is_directory": info.is_dir(),
                    "compressed_bytes": info.compress_size,
                    "uncompressed_bytes": info.file_size,
                    "compression_method": info.compress_type,
                    "crc32_hex": f"{info.CRC:08x}",
                    "flag_bits": info.flag_bits,
                    "modified_time": list(info.date_time),
                    "issues": sorted(set(member_issues)),
                }
                entries.append(entry)
                for issue in entry["issues"]:
                    issues.append({"code": issue, "member": name})

            if total_uncompressed > max_total_uncompressed:
                issues.append({
                    "code": "total_uncompressed_size_limit_exceeded",
                    "observed": total_uncompressed, "limit": max_total_uncompressed,
                })
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise ValueError(f"cannot inspect ZIP central directory: {exc}") from exc

    after_stat = path.stat()
    if (before_stat.st_size, before_stat.st_mtime_ns, before_stat.st_ino) != (
        after_stat.st_size, after_stat.st_mtime_ns, after_stat.st_ino
    ) or sha256_file(path) != archive_hash:
        raise ValueError("archive changed during inventory; discard this report and retry")

    return {
        "archive_path": str(path),
        "archive_bytes": path.stat().st_size,
        "archive_sha256": archive_hash,
        "inventory_mode": "central_directory_only_no_extraction",
        "member_count": len(entries),
        "file_count": sum(not entry["is_directory"] for entry in entries),
        "directory_count": sum(entry["is_directory"] for entry in entries),
        "total_declared_uncompressed_bytes": total_uncompressed,
        "total_declared_compressed_bytes": total_compressed,
        "csv_member_count": extension_counts.get(".csv", 0),
        "file_extension_counts": dict(sorted(extension_counts.items())),
        "filename_date_candidates": [
            {"date": value, "member_names": sorted(names),
             "calendar_status": "unverified_filename_candidate_only"}
            for value, names in sorted(filename_dates.items())
        ],
        "filename_date_candidate_count": len(filename_dates),
        "filename_date_parse_errors": filename_date_errors,
        "limits": {
            "max_entries": max_entries,
            "max_total_uncompressed_bytes": max_total_uncompressed,
            "max_member_uncompressed_bytes": max_member_uncompressed,
            "max_compression_ratio": max_compression_ratio,
        },
        "issues": issues,
        "safe_to_extract": not issues,
        "entries": entries,
        "policy": "inventory_only_review_required_before_decompression",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-entries", type=int, default=DEFAULT_MAX_ENTRIES)
    parser.add_argument("--max-total-uncompressed", type=int, default=DEFAULT_MAX_TOTAL_UNCOMPRESSED)
    parser.add_argument("--max-member-uncompressed", type=int, default=DEFAULT_MAX_MEMBER_UNCOMPRESSED)
    parser.add_argument("--max-compression-ratio", type=float, default=DEFAULT_MAX_COMPRESSION_RATIO)
    args = parser.parse_args()
    report = inspect_zip(
        args.archive,
        max_entries=args.max_entries,
        max_total_uncompressed=args.max_total_uncompressed,
        max_member_uncompressed=args.max_member_uncompressed,
        max_compression_ratio=args.max_compression_ratio,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "entries"}, indent=2))
    return 0 if report["safe_to_extract"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
