"""Extract only explicitly selected CSV members from a reviewed ZIP inventory."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import zipfile
from pathlib import Path, PurePosixPath

from inspect_floorsheet_archive import inspect_zip


def _sha256_stream(stream, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    stream.seek(0)
    for chunk in iter(lambda: stream.read(chunk_size), b""):
        digest.update(chunk)
    stream.seek(0)
    return digest.hexdigest()


def extract_reviewed_csv_members(
    archive_path: str | Path,
    output_dir: str | Path,
    *,
    member_names: list[str],
    expected_archive_sha256: str,
    max_total_extracted_bytes: int = 512 * 1024 * 1024,
    max_member_bytes: int = 128 * 1024 * 1024,
) -> dict:
    """Extract a caller-selected CSV allowlist after inventory/hash verification."""
    archive = Path(archive_path)
    if not isinstance(expected_archive_sha256, str) or len(expected_archive_sha256) != 64:
        raise ValueError("expected_archive_sha256 must be a 64-character SHA-256")
    if any(c not in "0123456789abcdef" for c in expected_archive_sha256.lower()):
        raise ValueError("expected_archive_sha256 must be hexadecimal")
    for name, value in (
        ("max_total_extracted_bytes", max_total_extracted_bytes),
        ("max_member_bytes", max_member_bytes),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if not isinstance(member_names, list) or not member_names:
        raise ValueError("member_names must be a non-empty list")
    if any(not isinstance(name, str) or not name for name in member_names):
        raise ValueError("member_names must contain nonblank strings")
    if len(set(member_names)) != len(member_names):
        raise ValueError("member_names must be unique")

    inventory = inspect_zip(archive)
    if not inventory["safe_to_extract"]:
        raise ValueError("archive inventory contains safety issues; extraction blocked")
    actual_archive_hash = inventory["archive_sha256"]
    if actual_archive_hash != expected_archive_sha256.lower():
        raise ValueError("archive SHA-256 does not match reviewed inventory")
    selected = set(member_names)
    known = {entry["name"]: entry for entry in inventory["entries"]}
    unknown = sorted(selected - set(known))
    if unknown:
        raise ValueError(f"selected members are absent from inventory: {unknown}")

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    resolved_root = output_root.resolve()
    extracted = []
    created_paths = []
    total_written = 0
    try:
        with archive.open("rb") as archive_stream:
            before = os.fstat(archive_stream.fileno())
            if _sha256_stream(archive_stream) != actual_archive_hash:
                raise ValueError("archive changed after inventory verification")
            with zipfile.ZipFile(archive_stream, "r") as zf:
                for member_name in member_names:
                    info = zf.getinfo(member_name)
                    if info.is_dir() or PurePosixPath(member_name).suffix.lower() != ".csv":
                        raise ValueError(f"selected member is not a CSV file: {member_name}")
                    if info.file_size > max_member_bytes:
                        raise ValueError(f"selected member exceeds max_member_bytes: {member_name}")
                    if total_written + info.file_size > max_total_extracted_bytes:
                        raise ValueError("selected members exceed max_total_extracted_bytes")
                    target = (resolved_root / Path(*PurePosixPath(member_name).parts)).resolve()
                    if target != resolved_root and resolved_root not in target.parents:
                        raise ValueError(f"selected member escapes output directory: {member_name}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        raise FileExistsError(f"refusing to overwrite existing extracted file: {target}")
                    temporary = target.with_name(target.name + ".extracting")
                    digest = hashlib.sha256()
                    written = 0
                    try:
                        with zf.open(info, "r") as source, temporary.open("xb") as sink:
                            created_paths.append(temporary)
                            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                                written += len(chunk)
                                total_written += len(chunk)
                                if written > max_member_bytes or total_written > max_total_extracted_bytes:
                                    raise ValueError("actual extracted bytes exceeded configured limits")
                                digest.update(chunk)
                                sink.write(chunk)
                        if written != info.file_size:
                            raise ValueError(f"extracted byte count differs from ZIP metadata: {member_name}")
                        if target.exists():
                            raise FileExistsError(f"refusing to overwrite existing extracted file: {target}")
                        os.link(temporary, target)
                        temporary.unlink()
                        created_paths.remove(temporary)
                        created_paths.append(target)
                    except Exception:
                        if temporary in created_paths and temporary.exists():
                            temporary.unlink()
                            created_paths.remove(temporary)
                        raise
                    extracted.append({
                        "member_name": member_name,
                        "output_path": str(target),
                        "byte_count": written,
                        "sha256": digest.hexdigest(),
                        "crc32_hex": f"{info.CRC:08x}",
                        "zip_crc_verified": True,
                    })
            after = os.fstat(archive_stream.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (
                after.st_size, after.st_mtime_ns, after.st_ino
            ):
                raise ValueError("archive file changed during extraction")
    except Exception:
        for created in reversed(created_paths):
            try:
                created.unlink(missing_ok=True)
            except OSError:
                pass
        raise

    return {
        "archive_path": str(archive),
        "archive_sha256": actual_archive_hash,
        "selected_member_count": len(member_names),
        "extracted_member_count": len(extracted),
        "total_extracted_bytes": total_written,
        "members": extracted,
        "promotion_allowed": False,
        "policy": "explicit_csv_allowlist_hash_pinned_no_overwrite",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--expected-archive-sha256", required=True)
    parser.add_argument("--member", action="append", required=True,
                        help="Exact CSV member path from the reviewed inventory; repeat for multiple members")
    parser.add_argument("--max-total-extracted-bytes", type=int, default=512 * 1024 * 1024)
    parser.add_argument("--max-member-bytes", type=int, default=128 * 1024 * 1024)
    parser.add_argument("--manifest-output", type=Path)
    args = parser.parse_args()
    result = extract_reviewed_csv_members(
        args.archive, args.output_dir, member_names=args.member,
        expected_archive_sha256=args.expected_archive_sha256,
        max_total_extracted_bytes=args.max_total_extracted_bytes,
        max_member_bytes=args.max_member_bytes,
    )
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.manifest_output:
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
