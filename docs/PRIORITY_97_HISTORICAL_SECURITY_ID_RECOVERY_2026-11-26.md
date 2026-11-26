# Priority 97 — historical security-ID recovery assessment (2026-11-26)

## Result

Historical predecessor security IDs were **not recovered** from the currently committed archives. The repository tree contains the dated 2026-11-25 security-list response and parsed snapshot, but no earlier dated security-master snapshots were located in the inspected data, history-starter, automation, or scanner repositories. The repeated raw security-list objects in the scanner repository share the same blob hashes and are copies of the same current snapshot, not independent historical observations.

## Provider acquisition lead

ShareHub's public API documentation describes:
- `GET /data/api/v1/nepse-data/companies`: symbol, company name, sector, listed shares, listing date, active status and instrument type. The documented company-row schema does not include a security ID.
- `GET /data/api/v1/nepse-data/stocks`: includes `nepseSecurityId`, symbol, name, instrument type and active status.
- Access requires a Data API account, a licensed service, Bearer authentication and server IP allow-listing.

Documentation: https://sharehubnepal.com/data/nepse-data-documentation/

No authenticated payload was obtained. Consequently there is no response status, raw response body or checksum to pin. The public documentation is a source lead only, not evidence of any predecessor's ID or historical ID validity.

## Current successor snapshot observations

The 2026-11-25 security snapshot records SLBSL 2804, NMLBBL 396, MATRI 694, SMATA 2761, SMPDA 2896, GBLBS 583 and PFL 236. Source blob: `ed548857eb550fbb237910eb903fc202751c63a1`.

These remain point-in-time successor observations only. They do not establish predecessor IDs, historical validity intervals, security-ID reuse, or legal continuity.

## Unresolved predecessor set

BPW, JALPA, KLBSL, MKLB, MMFDB, NLBBL, SABSL, SDLBSL, SAMAJ and SFCL remain unresolved. No ID is inferred from ticker similarity, successor name, current ID, or OHLCV filename.

## Safety controls

- Added machine-readable acquisition status and explicit promotion prohibitions to `data/reference/nepse_historical_identity_evidence_2026-11-26.json`.
- Added regression tests ensuring predecessor stable IDs remain null, the successor snapshot remains date-scoped, provider documentation is not represented as acquired data, and no history/universe/training promotion is authorized.
- No OHLCV/floorsheet records were changed; no histories were spliced.

## Next required input

Obtain a permitted authenticated ShareHub Data API export (including the `stocks` response) or dated historical security-master snapshots from another source. Preserve raw bytes, retrieval timestamp, response status, URL, and SHA-256 before parsing. Then reconcile each predecessor ID against dated corporate-action/listing/suspension evidence and floorsheet/price records.

**Status:** source discovery and safety guard completed; historical ID recovery remains blocked on actual dated source payloads.
