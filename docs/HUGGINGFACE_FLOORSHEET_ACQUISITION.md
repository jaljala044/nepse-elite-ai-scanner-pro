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

- Workflow run: [hf-dataset-inventory #?](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45406145702)
- Pinned dataset commit: `11ef83a9c3cdbe78112f0245451cdc52bdb1a8f0`
- Dated floorsheet files: **603**
- Unique dates: **603** (no duplicate dated paths in the manifest)
- Date span: **2024-01-02 through 2026-08-26**
- Sum of compressed file sizes: **758,924,600 bytes** (about 723.8 MiB)
- Every one of the 603 entries includes an LFS SHA-256 and Xet hash in Hub metadata.
- Manifest JSONL SHA-256: `a6975a14059aaf63b66435589ea5ce81558986f015b9d93a02ebdea13e2565fb`
- Manifest file: `urekmazino69_Nepse-floorsheet-and-indices_11ef83a9c3cd.jsonl`
- GitHub Actions artifact SHA-256: `2643bca1f5511f2d584c62628e7c7d50c421f2460e8e903a73a695b986c9ce69`

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
  2025-09-18 following the September protests ([B360, 12 September 2025](https://www.b360nepal.com/detail/26407/capital-market-to-remain-closed-till-sep-18); [ShareSansar, 12 September 2025](https://www.sharesansar.com/index.php/newsdetail/nepse-announces-temporary-closure-of-secondary-market-trading-2025-09-12)). This is a strong closure lead, but
  the primary dated NEPSE notice still needs to be captured and hashed.
- 2025-09-28 to 2025-10-07 overlaps the Dashain period and the reported NEPSE
  decision to keep trading closed on 2025-10-06, resuming on 2025-10-07 ([Taksar, 6 October 2025](https://en.taksarnews.com/2025/10/3948/)). The
  primary exchange notices and exact daily closure interval still need archiving.

These reports explain why the gaps may be legitimate closures; they do not turn the
dates into verified calendar rows. Keep them as review leads until the original
NEPSE notices or independently verified exchange records are archived.

The initial evidence-backed calendar file is now present at
`data/reference/nepse_session_calendar.csv` with its required header and **no
verified date rows yet**. It is intentionally empty: do not mistake a blank
template for a completed calendar or a passing integrity gate.

### Date-level matrix result — 2026-11-24

The same successful workflow generated
`artifacts/source-manifests/nepse-calendar-coverage-matrix.json` over the full
manifest span:

- Matrix SHA-256: `f6013381d5e6293375f63609bf5de16c5f726752f0bc28bfa63f76c9f80fe21f`
- Calendar days represented: **968**
- Dated source files observed: **603**
- Dates with explicit verified NEPSE calendar evidence: **0**
- Unverified regular-session weekday candidates: **692**
- Unverified non-session weekday candidates: **276**
- Candidate dates with no floorsheet file: **89**
- Files on schedule non-session candidates: **0**

The 89 candidate dates without a file are **not confirmed missing trading days**;
many may be public holidays, exceptional closures, or publisher gaps. The matrix
deliberately leaves all 968 dates unverified because the calendar template has no
evidence rows yet. This is the correct fail-closed outcome, not a successful
calendar gate.

## 90–120 recent-date acquisition target — live source inventory, 2026-11-24

The project now uses **90 verified NEPSE sessions as the minimum viable target and
120 as the preferred initial target**. The target is measured in exchange sessions,
not calendar days. A dated archive file is only a candidate observation until its
date is reconciled to the evidence-backed session calendar.

A live manifest-only run inventoried three public floorsheet archives:

| Source | Pinned revision | Dated files | First date | Latest date |
|---|---|---:|---|---|
| SocrateAI | `cfa92493e93211c7019a5cd0b2cbe7d400d9c4e3` | 661 | 2024-01-01 | 2026-11-24 |
| SamirWagle | `144cecb36f110bedb741f5d147c7857cdb24c958` | 179 | 2026-02-22 | 2026-11-24 |
| Urekmazino HF | `11ef83a9c3cdbe78112f0245451cdc52bdb1a8f0` | 603 | 2024-01-02 | 2026-08-26 |

The latest **120 distinct dates with at least one source file** span
**2026-06-03 through 2026-11-24**. Within those 120 candidate dates:

- SamirWagle has files on 112 dates.
- SocrateAI has files on 110 dates.
- Urekmazino has files on 60 dates (its archive ends 2026-08-26).
- 58 dates have all three sources; 46 dates have two sources; 16 dates have one source.

This is promising evidence that a recent 90–120-date working set can be assembled.
It is **not yet a verified 120-session dataset**. The calendar file currently has
zero evidence-backed open-session rows, so the strict target builder correctly
reports 0 verified sessions selected and both target gates false. The 120-date
preview is retained separately so it can guide calendar reconciliation without
being mislabelled as confirmed trading sessions.

The workflow used manifest-only enumeration; **no raw floorsheet transaction rows
were downloaded**. The two GitHub projects have different stated reuse conditions
and upstream data-lineage questions, so a raw download must wait for rights review.
For now, the next work is to reconcile the 120 candidate dates to dated NEPSE
session/closure evidence, then select the latest 90–120 confirmed sessions and
acquire only rights-cleared files for row-level validation.

Manifest SHA-256 values:
- SocrateAI: `63b663e7b2a40d335d46020831c4649c4036fbe3b7c283c33864ef59dd0fdc9b`
- SamirWagle: `400472ba1ca8de623e9425bf788258cc2df10b30c5a2839f0d73c90865b19420`
- Urekmazino: `b29318fa6bf4a4b5ab024b0bb7ad5c076699550c7e3109e4ac51c85d7fda3f74`

The full manifests, date-level matrix and recent-target report are preserved in
GitHub Actions artifact
[`nepse-hf-data-inventory`](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45406656390),
SHA-256 `cec24ff2f94dafacb40ccf59204bf886b0af82b7c5c2e1e1ff7a715d2bf5d0be`,
retained through **2027-02-22**.
