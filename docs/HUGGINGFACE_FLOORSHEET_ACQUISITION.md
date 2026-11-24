# Hugging Face NEPSE floorsheet acquisition

## Source candidate

Dataset: [urekmazino69/Nepse-floorsheet-and-indices](https://huggingface.co/datasets/urekmazino69/Nepse-floorsheet-and-indices)

The publisher declares MIT and says the floorsheet archive covers 2024-01-02 through 2026-08-26. The public floorsheet folder page reports about 759 MB and lists gzip-compressed daily files. A sample file page exposes a SHA-256 pointer and compressed size for 2024-03-18. These are publisher/Hugging Face metadata claims, not an exchange completeness certification.

The public dataset viewer fails to build its table because a contract number is cast to int64. The preview also renders \`time\` as null. Our ingestion must preserve \`contract_no\` as text and must not synthesize execution times.

## Manifest-only inspection

The project utility \`backend/acquire_hf_floorsheet_archive.py\` uses the Hugging Face Hub client and public, unauthenticated access:

\`\`\`bash
python backend/acquire_hf_floorsheet_archive.py \\
  --repo-id urekmazino69/Nepse-floorsheet-and-indices \\
  --path floorsheet \\
  --revision main \\
  --output artifacts/source-manifests
\`\`\`

It resolves the branch to an immutable commit, paginates the Hub file tree, and records each dated CSV/CSV.GZ file's path, byte size, blob ID, LFS SHA-256 metadata and Xet hash when available. No raw trade data is downloaded in this mode.

## Bounded download mode

Use only after confirming upstream data-use rights for the intended private use:

\`\`\`bash
python backend/acquire_hf_floorsheet_archive.py \\
  --repo-id urekmazino69/Nepse-floorsheet-and-indices \\
  --path floorsheet \\
  --revision main \\
  --output artifacts/source-manifests \\
  --raw-root data/raw/huggingface \\
  --download \\
  --confirm-data-rights \\
  --max-total-bytes 900000000
\`\`\`

Download mode requires explicit flags, a positive total-byte ceiling, and per-file LFS SHA-256 metadata. It verifies actual size and SHA-256 before immutable promotion. If the Hub does not expose a content SHA-256 for a file, the utility refuses to promote that file. It uses public unauthenticated access only; it does not request credentials or bypass access controls.

## What this does not prove

- A successful Hub download and matching SHA-256 prove byte integrity against Hub metadata, not correctness or completeness of the publisher's transaction rows.
- The dataset's MIT card does not independently establish upstream rights for every underlying NEPSE record.
- Missing dates must be reconciled against the verified NEPSE session calendar; filenames alone do not establish holidays or missed sessions.
- Contract numbers must remain strings; the viewer's int64 conversion error is a warning against numeric coercion.
- Empty/missing execution times remain null and must not be imputed.
- All rows still require schema, date, duplicate/conflict, quantity/rate/amount, broker-code, contract-ID, and daily control-total audits before canonical ingestion.
