# P1 evidence manifest contracts

Updated: 2026-11-25

These templates are empty acquisition contracts, not evidence. Never populate
them with guessed hashes, dates, source rights, identities or calendar claims.
The integrated audit must read the actual files and raw bytes before a gate can
pass.

## 1. Immutable raw source objects

Template: `data/evidence/templates/source-object-manifest.template.jsonl`

One JSON object per acquired raw file. Required fields:
- `source_id`: stable source/publisher identifier.
- `path`: source-relative path.
- `sha256`: SHA-256 of the downloaded raw bytes.
- `local_path`: optional path below `data/raw/`.

Recommended additional fields: `repository`, `revision` (immutable commit),
`blob_oid`, `lfs_oid`, `byte_count`, `retrieved_at_utc`, `source_uri`,
`published_at`, `rights_status`, `rights_evidence_uri`, `lineage_notes`,
`content_type`. Never use a Git blob SHA-1 as a substitute for the local
payload SHA-256.

## 2. Source-file date manifest

Template: `data/evidence/templates/source-file-date-manifest.template.jsonl`

One JSON object per date-bearing file. Required by the calendar coverage CLI:
`date` (YYYY-MM-DD), `path`, and one source identifier among `repo_id`,
`repository`, `source_id`, or `source`. Include `size_bytes`, immutable
`revision`, `blob_oid`, and `sha256` when available. A dated file is not
proof that the date was a trading session.

## 3. Calendar evidence

Template: `data/evidence/templates/calendar-evidence-manifest.template.json`

Top-level arrays: `captures` and `claims`. A capture requires unique
`source_id`, approved official HTTPS `final_url`/`url`, exact
`raw_evidence_path`, `raw_evidence_sha256` and timezone-aware UTC
`retrieved_at_utc`. A claim requires ISO `date`, explicit verified status,
`scope`, and a non-empty list of captured `source_ids`. Opposing open/closed
claims with overlapping scope remain conflicts. Secondary reports and
government holiday calendars are leads, not primary NEPSE proof.

## 4. Corporate-action review

Template: `data/evidence/templates/corporate-action-review.template.csv`

One row per symbol/action/effective event. Preserve announcement, ex, record
and effective dates separately; record exact terms, source URI and hash, and
review status. No adjusted OHLCV series may be produced until action terms,
security identity, adjustment method and effective date are reviewed.

## 5. OHLCV conflict ledger

Template: `data/evidence/templates/ohlcv-conflict-ledger.template.csv`

One row per symbol/date/source pair. Preserve both immutable source revisions,
paths, file hashes and full OHLCV tuples. A primary evidence reference and hash
are required to resolve a conflict. External vendor agreement is corroboration,
not automatic primary exchange proof. Until resolved, keep both source values
and quarantine the date from canonical training.

## 6. Broker party observations

Expected normalized file:
`data/normalized/broker-party-observations.csv`.

Required columns:
`trade_date,symbol,side,amount,quantity,identity_status,broker_entity_id,source_id,contract_id,source_payload_sha256,source_row_number,identity_evidence_ids`.

Each trade contract yields separate buyer and seller party observations.
Broker codes identify execution channels; do not infer beneficial ownership.
Keep raw trade rows separate from daily broker aggregates and preserve the
source payload hash and row number for every observation.

## 7. Promotion rule

Empty templates, repository file listings, metadata-only inventories and
successful software tests do not satisfy evidence gates. Only captured raw
objects with matching hashes, complete source lineage/rights review, verified
calendar evidence, reconciled OHLCV/corporate actions, broker identity policy
and point-in-time checks may contribute to a P1 acceptance decision.
