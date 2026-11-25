# Floorsheet ZIP inventory and safe review guide

**Date:** 2026-11-25  
**Tool:** `backend/inspect_floorsheet_archive.py`

## Purpose

Inventory a large floorsheet ZIP before extraction or parsing. The tool reads the ZIP central directory and streams the outer archive once to calculate SHA-256. It does **not** decompress, extract, rename, or modify any member.

## Run

From the repository root:

```bash
python backend/inspect_floorsheet_archive.py /path/to/floorsheet-archive.zip \
  --output data/reports/floorsheet-archive-inventory.json
```

The report records:
- Exact archive byte count and SHA-256.
- Member names, directory/file counts, compressed and declared uncompressed sizes, CRC32, compression method, flags and ZIP timestamps.
- CSV member count and file-extension counts.
- Duplicate names, case-insensitive name collisions, path traversal/absolute paths, backslash paths, symbolic links, encrypted members, suspicious compression ratios and size/entry-limit violations.

## Default bounds

| Control | Default |
|---|---:|
| Maximum members | 200,000 |
| Maximum total declared uncompressed bytes | 20 GiB |
| Maximum one member declared uncompressed size | 2 GiB |
| Maximum compression ratio | 1,000:1 |

The limits can be tightened for a particular source. Increasing them should require an explicit review of archive size and origin.

## Interpretation

- `safe_to_extract=true` means only that the inventory found no configured structural/size hazard. It is **not** proof that the data is authentic, complete, licensed, correctly dated, or suitable for canonical use.
- `safe_to_extract=false` means do not extract until every reported issue is reviewed.
- CRC32 is ZIP-level corruption detection, not a cryptographic provenance digest for each member.
- The archive SHA-256 pins the exact outer ZIP bytes. A future member-content processing step must also record per-member SHA-256 values.
- No ZIP member should be treated as a trading session or a complete floorsheet date merely because its filename resembles a date.
- After inventory, inspect a small representative CSV sample and approve an explicit source-header mapping before bulk normalization.

## Safety

The tool does not extract files and does not follow archive paths onto the filesystem. It uses only ZIP metadata to make a bounded preflight report. Do not promote any archive or its contents into canonical/training datasets based only on this inventory.
