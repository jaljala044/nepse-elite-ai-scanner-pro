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

## One-date raw sample acquisition and row audit — 2026-11-24

A single file was acquired from the pinned MIT-declared dataset commit
`11ef83a9c3cdbe78112f0245451cdc52bdb1a8f0` for **2026-08-26**:

- Path: `floorsheet/2026-08-26.csv.gz`
- Compressed bytes: **1,046,475**
- Hub LFS SHA-256 and local SHA-256 both:
  `2d199262617e5e7bf385c486104228eb6ff8dff7284cf8b32562490dad3da89e`
- Rows: **61,442**
- Unique contract numbers: **61,442**; duplicate contracts: **0**
- Unique row IDs: **61,442**; duplicate IDs: **0**
- Date mismatches / contract-date-prefix mismatches: **0**
- Quantity × rate versus amount arithmetic errors: **0**
- Invalid buyer/seller broker identifiers: **0**
- Missing execution times: **0**; observed time range: **10:46:00–14:59:59**
- Unique symbols: **348**; unique broker codes across buyer/seller: **91**
- Total share quantity: **13,582,320**
- Sum of transaction amounts: **NPR 4,773,857,657.46**

The raw file's time field is populated even though the Hugging Face viewer preview
rendered it as null. The raw CSV, not the preview, is the inspected evidence.
Contract numbers and IDs remain strings. No row was deduplicated or corrected.

### Same-day index-control conflict — do not promote this date yet

The matching Urekmazino `indices/2026-08-26.csv.gz` file was also acquired and
hash-verified. Its NEPSE Index row reports turnover **NPR 4,693,373,201.62**,
share volume **11,568,032**, and **60,740** transactions. Compared with the
floorsheet sample, the differences are:

- Turnover: **NPR 80,484,455.84**
- Share quantity: **2,014,288**
- Transaction count: **702**

Its OHLC row also has `open=2594.27` and `high=2592.12`, so high is below open.
The open equals the prior close implied by close minus absolute change. This is
an index-row anomaly, not something to correct automatically.

Cross-source evidence is conflicting:

- The pinned SocrateAI adjusted-index CSV reports turnover `4,773,850,987`,
  only **NPR 6,670.46** below the floorsheet amount sum. Its OHLC values differ
  slightly from the Urek index row.
- The YONEPSE mirror and Urek index row agree on **60,740** trades and
  **NPR 4.693 billion**, but YONEPSE is a third-party mirror whose publisher
  disabled TLS verification in its scraper.
- Hamroshare's 26-August market-wrap page reports **60,740** trades and
  **NPR 4.69 billion**, agreeing with the Urek/YONEPSE index controls:
  https://hamroshare.com.np/news/market-wrap/2026-08-26
- Hamroshare's historical-market table reports **61,442** transactions,
  **1.36 crore** shares and **NPR 4.77 billion** for the same date:
  https://hamroshare.com.np/nepse/historic-market
- OnlineKhabar and Nepal News report turnover of about **NPR 4.77 billion**;
  Nepal Life Capital's published turnover chart shows
  **NPR 4,773,857,657.45**:
  https://english.onlinekhabar.com/nepse-fall-rasuwa-flood-hydropower.html
  https://english.nepalnews.com/s/business/nepal-news-evening-economic-brief-august-26-2026/
  https://nepallifecapital.com.np/uploads/newsletter/01M1DMR5S56C3SHT7HR1PJ1YF9.pdf

These sources do not yet resolve whether the index control row is stale/partial,
whether the floor file contains records outside the index control definition, or
which secondary report is authoritative. Preserve both datasets and every
difference. The floorsheet's row-level validation passes, but the combined
sample gate remains **FAIL** because the same-dataset index controls conflict
and the index OHLC row is invalid. `canonical_promotion_allowed=false`.

Workflow run 45412604263, artifact 14930540759, contains the two hash-verified
raw sample files and the complete audit report. It is a diagnostic artifact,
not a canonical-data import.

### Scope diagnosis from sector-level controls

A sector-by-sector comparison shows why the aggregate totals must not be treated
as a simple completeness check:

- Exact row/quantity/turnover matches: Development Banks, Hotels and Tourism,
  Hydro Power, Manufacturing and Processing, Microfinance, Others, and Trading.
- Sector differences: Commercial Banks (+82 floorsheet rows), Finance (+1),
  Investment (+162), Life Insurance (+3), Non-Life Insurance (+30), and Mutual
  Fund (-42).
- The floorsheet contains **59 Non-Convertible Debenture** rows for which the
  index file has no corresponding sector row.
- The Urek index file's sector rows sum to **61,147** transactions, including
  **407** Mutual Fund transactions. Removing the Mutual Fund sector gives
  exactly **60,740**, the NEPSE Index aggregate transaction count. The same
  relationship holds for turnover and share volume: the aggregate NEPSE Index
  row excludes the Mutual Fund sector.

This demonstrates that the NEPSE Index aggregate is not a directly comparable
control total for every instrument in the raw floorsheet. After excluding the
365 Mutual Fund and 59 debenture rows in the floorsheet, a further 278
transactions remain across five sector differences. The exact eligible-
instrument/constituent scope for those differences is still unresolved. Do not
label them missing or extra transactions without a verified scope mapping.

The open-field anomaly remains independent: the Urek index sample stores
`open=2594.27`, which equals the prior close derived from
`close - absolute_change`; the same-day market report and YONEPSE mirror report
an actual open near **2591.32**. Preserve the raw Urek value and flag the field
mapping problem; never overwrite it with the third-party value.

The correct interpretation is therefore:
- **Floorsheet row checks:** pass for this one sample date.
- **Index aggregate and sector controls:** scope/value reconciliation required.
- **Canonical promotion:** still blocked; this one-day sample does not prove
  completeness across dates or establish point-in-time availability.

## Same-day transaction-level cross-check against SocrateAI

A second raw sample was acquired from the pinned SocrateAI repository commit
`cfa92493e93211c7019a5cd0b2cbe7d400d9c4e3` for the same date
**2026-08-26**:

- Path: `floorsheet/floorsheet_2026-08-26.csv`
- Bytes: **3,588,067**
- Git blob SHA-1:
  `86a7819b5f106bea73b1a0741df6295d5bd53920`
- SHA-256:
  `d95dca06df551df977a5253d200e70bfdeb958be3e96ec08b021832600af2e21`

Transaction-level comparison against the Urekmazino sample:

- Urekmazino rows: **61,442**; SocrateAI rows: **61,442**
- Shared contract numbers: **61,442**
- Urekmazino-only / SocrateAI-only contracts: **0 / 0**
- Duplicate contract numbers in either source: **0**
- Differences across shared fields (symbol, buyer, seller, quantity, rate,
  amount and trade date): **0**

This is an exact match across all shared transaction fields for one day. It
strongly corroborates the transaction rows, but does not establish independent
upstream provenance: the two publishers may consume the same upstream source.
SocrateAI's sample schema has no execution-time, sector or row-ID fields, so
Urekmazino's `time`, `sector` and `id` columns are not independently checked.
No rows are merged or promoted. Both raw samples remain separately stored in
the private workflow artifact for review.

The one-day match does not prove the other 119 candidate dates are complete.
Bulk acquisition remains gated on rights review, source-scope reconciliation,
calendar evidence and repeated date-level cross-checks.
