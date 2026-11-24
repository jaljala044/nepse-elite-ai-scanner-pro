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

## Live manifest-only enumeration — 2026-11-24

A GitHub Actions run successfully enumerated the complete dated floorsheet folder
without downloading any raw floorsheet rows:

- Workflow run: [hf-dataset-inventory #?](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45405942918)
- Pinned dataset commit: `11ef83a9c3cdbe78112f0245451cdc52bdb1a8f0`
- Dated floorsheet files: **603**
- Unique dates: **603** (no duplicate dated paths in the manifest)
- Date span: **2024-01-02 through 2026-08-26**
- Sum of compressed file sizes: **758,924,600 bytes** (about 723.8 MiB)
- Every one of the 603 entries includes an LFS SHA-256 and Xet hash in Hub metadata.
- Manifest JSONL SHA-256: `222f548490d3967d47c983bc628114a6fedcd00c9192c3fc1eabc8b9a8e9eaeb`
- Manifest file: `urekmazino69_Nepse-floorsheet-and-indices_11ef83a9c3cd.jsonl`
- GitHub Actions artifact SHA-256: `52f6fb44ef6df0d238454809b9b3dfed17e1e6551ccb19c00794c86f342684fa`

Annual file counts: 2024 = 226, 2025 = 223, 2026 = 154.

This confirms the repository's file inventory and Hub-provided integrity metadata at
the pinned revision. **It does not confirm row counts, transaction completeness,
correctness, or NEPSE session coverage.** No raw floorsheet files were downloaded.
The two largest calendar gaps in the folder manifest are 2025-09-08 to 2025-09-18
and 2025-09-28 to 2025-10-07; treat them as reconciliation targets only, not
automatically as missing trading sessions.

The artifact is retained by GitHub Actions for **90 days** (through 2027-02-22).
Download and preserve it in the project's immutable evidence vault before expiry.

### Calendar reconciliation leads

NEPSE exposes a public [Holiday Listing](https://www.nepalstock.com/holiday-listing)
page. Its current web-rendered response exposed the column headings but no readable
dated rows to this audit, so no closure dates were imported from it.

The two largest floorsheet file gaps need careful interpretation:
- 2025-09-08 to 2025-09-18 overlaps the reported NEPSE suspension through
  2025-09-18 following the September protests. This is a strong closure lead, but
  the primary dated NEPSE notice still needs to be captured and hashed.
- 2025-09-28 to 2025-10-07 overlaps the Dashain period and the reported NEPSE
  decision to keep trading closed on 2025-10-06, resuming on 2025-10-07. The
  primary exchange notices and exact daily closure interval still need archiving.

These reports explain why the gaps may be legitimate closures; they do not turn the
dates into verified calendar rows. Keep them as review leads until the original
NEPSE notices or independently verified exchange records are archived.

The initial evidence-backed calendar file is now present at
`data/reference/nepse_session_calendar.csv` with its required header and **no
verified date rows yet**. It is intentionally empty: do not mistake a blank
template for a completed calendar or a passing integrity gate.
