# NEPSE floorsheet archive acquisition utility

## Current source-manifest evidence

The 2026-11-24 manifest audit found:

- SocrateAI: 658 dated CSV files, 3,116,744,322 declared bytes.
- SamirWagle: 179 dated CSV files, 734,702,749 declared bytes.
- 155 shared filename dates; zero byte-identical Git blobs.
- 11 shared dates where Samir's file is more than 10% smaller than SocrateAI's. These are investigation priorities, not proof of missing rows.

See [FLOORSHEET_SOURCE_MANIFEST_AUDIT_2026-11-24.md](FLOORSHEET_SOURCE_MANIFEST_AUDIT_2026-11-24.md) for pinned tree hashes and details.

## Manifest-only run

The utility is in \`backend/acquire_floorsheet_archive.py\`. It uses only Python's standard library.

From the repository root:

\`\`\`bash
python backend/acquire_floorsheet_archive.py \\
  --owner socrateai-official \\
  --repo nepse-open-data \\
  --ref main \\
  --prefix floorsheet \\
  --output artifacts/source-manifests
\`\`\`

This resolves the branch to a commit SHA, enumerates dated CSV paths and Git blob IDs, and writes a JSONL manifest. It does not download transaction data.

## Download mode — rights clearance required

Do not use download mode until the dataset's upstream lineage and data-use rights have been reviewed and the intended use is permitted. A repository-level MIT license is not, by itself, proof that the publisher owns all upstream exchange or third-party data rights.

After clearance, a bounded download command is:

\`\`\`bash
python backend/acquire_floorsheet_archive.py \\
  --owner socrateai-official \\
  --repo nepse-open-data \\
  --ref main \\
  --prefix floorsheet \\
  --output artifacts/source-manifests \\
  --raw-root data/raw/floorsheet \\
  --download \\
  --confirm-data-rights \\
  --max-total-bytes 4000000000
\`\`\`

The utility refuses download mode without both explicit flags and a positive total-byte ceiling. It stores files under repository/commit/path, verifies declared size and the Git blob SHA-1 before promotion, records local SHA-256, uses atomic no-overwrite file promotion, and appends progress to a per-commit manifest. Re-running against the same commit resumes completed files and verifies already-present files rather than replacing them.

## Safety and validation limits

- The tool only enumerates dated \`.csv\` files under the requested path prefix.
- It refuses truncated Git tree responses.
- It does not classify weekends, holidays, or missing filenames as exchange sessions.
- Git blob verification proves the downloaded bytes match the Git object advertised by that repository; it does not prove the CSV is complete, accurate, exchange-origin, or licensed for reuse.
- It does not normalize or promote records into canonical storage.
- Row-level validation remains a separate required gate: schema, date, contract IDs, duplicate/conflict audit, amount arithmetic, broker codes, timestamp nullability, row counts, daily control totals, and cross-source contract-set reconciliation.
- Raw files are not to be committed to the application repository. Store them in the designated immutable data vault with source manifests and access controls.

## Tests

The backend test suite covers date extraction, invalid dates, Git blob hashing, and existing-file verification. The acquisition utility is not considered production-cleared until rights review and a controlled small-file acquisition test have also passed.
