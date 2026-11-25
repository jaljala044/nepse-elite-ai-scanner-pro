# Urek floorsheet source profile — 2026-11-25

## Source identity

- Dataset: [urekmazino69/Nepse-floorsheet-and-indices](https://huggingface.co/datasets/urekmazino69/Nepse-floorsheet-and-indices)
- Pinned revision used by the repository's sample/window acquisition workflow: \`11ef83a9c3cdbe78112f0245451cdc52bdb1a8f0\`
- Folder: \`floorsheet/\`
- Example sample date already present in that workflow: \`2026-08-26\`
- Dataset card declares an MIT license and describes its content as compiled from public NEPSE floorsheet/index data. This is publisher-declared licensing and lineage, not independent proof of upstream rights.

## Declared header mapping

| Canonical field | Exact declared source header | Treatment |
|---|---|---|
| trade_date | \`calculation_date\` | Parse as a date; do not infer from contract number |
| contract_id | \`contract_no\` | Keep as a string, including any leading zeros |
| symbol | \`stock_symbol\` | Normalize case only after preserving raw payload |
| buyer_broker_code | \`buyer\` | Broker execution-channel code |
| seller_broker_code | \`seller\` | Broker execution-channel code |
| quantity | \`quantity\` | Decimal/integer validation |
| rate | \`rate\` | Decimal validation |
| amount | \`amount\` | Decimal validation and quantity × rate reconciliation |

The dataset card also declares \`time\`, \`sector\` and \`id\`. These remain source-only fields in this canonical contract adapter. The raw CSV must be retained unchanged so none of those columns are irrecoverably lost. The public dataset preview shows \`time\` as null; no execution time or intraday order is synthesized from it.

## Implementation

- \`backend/app/floorsheet_source_profiles.py\` holds the explicit source map and exact header review.
- \`backend/tests/test_floorsheet_source_profiles.py\` exercises header mismatch rejection and a synthetic CSV adapter round-trip, including preservation of contract numbers as strings.
- The profile is explicitly marked \`publisher_schema_declared_raw_header_not_yet_reviewed\`. A successful synthetic unit test does **not** verify the physical source file.
- The existing sample acquisition path is in \`.github/workflows/hf-dataset-inventory.yml\`; it pins the revision, acquires bounded files, runs row/control-total audits and uploads the audit artifact.

## Acceptance status

- Source and declared schema located: **complete**.
- Canonical header mapping specified: **complete at publisher-schema level**.
- Exact sample CSV bytes/hash reverified in this work session: **not yet complete**.
- Physical sample header independently reviewed in this work session: **not yet complete**.
- Source rights and completeness independently established: **not complete**.
- Canonical/training promotion: **not allowed**.

The next required evidence is the raw sample file plus its file SHA-256 and exact header row, followed by a rerun of the source-specific floorsheet audit. Matching the declared schema is only a mapping gate; it is not proof that all rows, dates or broker records are complete.
