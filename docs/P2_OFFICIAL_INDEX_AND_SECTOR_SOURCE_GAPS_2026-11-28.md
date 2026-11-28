# P2.02 / P2.03 — official NEPSE source capture gap register (2026-11-28)

## Purpose

Record what can and cannot be established from the publicly indexed NEPSE first-party pages during this research pass. This is a discovery checkpoint, not an official API capture or a data promotion.

## First-party pages located

- NEPSE stocklist: https://www.nepalstock.com.np/stocklist
- NEPSE English catalogue: https://www.nepalstock.com.np/en/catalogue
- NEPSE home: https://www.nepalstock.com.np/

The indexed stocklist content exposes a current index/market snapshot and market lists. The indexed catalogue content exposes symbol-level quote/listing content. The indexed page excerpts were crawled earlier than this report and are not retained raw HTTP response bodies. They therefore cannot support a point-in-time 2026-11-28 claim, historical index history, or effective-dated sector membership.

## P2.02 — historical index graph/history

Previously discovered candidate routes remain third-party reverse-engineered references only:

- `POST /api/nots/graph/index/{id}`
- `GET /index/history/{id}`

The current research pass did not obtain:
- an official first-party frontend request contract;
- a request body/query schema from NEPSE;
- a successful TLS-verified direct response with HTTP status and content type;
- retained response bytes and SHA-256;
- date-range/pagination/history-depth evidence;
- a validated index identity and date-completeness report.

**Disposition:** `discovery_only`; `evidence_gate_passed=false`; `promotion_allowed=false`.

## P2.03 — effective-dated sector membership

The official indexed catalogue/stocklist excerpts do not provide a retained, source-backed effective-dated security-to-sector mapping in this research pass. A current display or current sector label cannot be backdated. No historical sector assignment is inferred from today's classification.

Still required:
1. An official NEPSE or SEBON record explicitly linking stable security identity to sector and effective date.
2. Original bytes, URL, retrieval time, HTTP status, content type, TLS/hostname validation, byte count and SHA-256.
3. Identity lifecycle handling for symbol changes, listings, suspensions, delistings and reclassifications.
4. A reconciliation report against the 281-equity manifest, with unmatched/duplicate/conflicting records retained as UNKNOWN.
5. Independent source review before a deployment-pinned membership manifest is admitted.

**Disposition:** `discovery_only`; `verified=false`; `admission_allowed=false`.

## Safe next action

Obtain a direct, authorized first-party browser/network capture from NEPSE or a formal source response. Preserve request/response metadata and raw bytes. Do not reverse-engineer credentials, bypass access controls, or disable TLS verification. Until then, the existing sector rotation calculator may run only on explicitly labelled research inputs and must not be presented as official sector history.

## Non-claims

- No official index-history API contract has been verified.
- No official effective-dated sector membership dataset has been acquired.
- No source payload or checksum is claimed by this note.
- No index, sector, OHLCV, canonical, backtest or scanner dataset was modified or promoted.
