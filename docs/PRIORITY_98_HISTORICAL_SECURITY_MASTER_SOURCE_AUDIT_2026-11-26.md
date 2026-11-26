# Priority 98 — historical security-master recovery source audit (2026-11-26)

## Acceptance decision

**Priority 98 source-discovery and repository-audit work is CLOSED. Historical ID recovery is NOT CLOSED and remains a hard external-data dependency.** This closes the discovery task only; it does not close Priority 97, approve historical identity assignments, or authorize price-history splicing/training.

## Scope searched

Reviewed the current project evidence and searched the available repository archives/code for dated historical security-master snapshots, predecessor symbol-to-ID crosswalks, raw security-list API payloads, and archived stock/security catalogues across:

- `jaljala044/nepse-elite-ai-scanner-pro`
- `jaljala044/nepse-smc-data`
- `jaljala044/nepse-history-starter`
- `jaljala044/nepse-automation`

The scanner repository contains the dated 2026-11-25 security snapshot and current successor mappings, but the inspected archives do not contain dated predecessor security-master snapshots for BPW, MMFDB, NLBBL, JALPA, KLBSL, MKLB, SABSL, SDLBSL, SAMAJ or SFCL. Repeated copies of the current security-list response are not independent historical observations.

## Provider path established

ShareHub's current API documentation describes `GET /data/api/v1/nepse-data/stocks`, whose response schema includes `nepseSecurityId`, `symbol`, `name`, instrument type and active status. The same documentation says API access requires a Data API account, licensed service entitlement, Bearer authentication and server-IP allow-listing. Its documented `/companies` endpoint includes symbol/company/listing information but does not document a security-ID field in the company rows.

Documentation: https://sharehubnepal.com/data/nepse-data-documentation/

The public NEPSE unofficial API client code also demonstrates that the exchange security list is a separate response from the company list and that a current symbol-to-security-ID map is derived from that response. It does not supply dated historical snapshots for the predecessor instruments:
https://github.com/basic-bgnr/NepseUnofficialApi/blob/master/nepse/NepseLib.py

## Results

- Historical predecessor IDs recovered: **0 / 10**.
- Historical validity intervals established: **0 / 10**.
- New authenticated/licensed provider payloads acquired: **0**.
- Current successor IDs remain date-scoped to the 2026-11-25 snapshot only.
- No predecessor ID was guessed from a current ID, ticker, company ID, listing notice, merger date or OHLCV row.
- No canonical identity assignments, price splices, raw-data edits or training promotion were made.

## Unresolved records

| Predecessor symbol | Successor | Historical security ID | Validity interval | Status |
|---|---|---:|---|---|
| BPW | SLBSL | null | null | Blocked — historical snapshot unavailable |
| MMFDB | NMLBBL | null | null | Blocked — historical snapshot unavailable |
| NLBBL | NMLBBL | null | null | Blocked — historical snapshot unavailable |
| JALPA | MATRI | null | null | Blocked — historical snapshot unavailable |
| KLBSL | MATRI | null | null | Blocked — historical snapshot unavailable |
| MKLB | SMATA | null | null | Blocked — historical snapshot unavailable |
| SABSL | SMPDA | null | null | Blocked — historical snapshot unavailable |
| SDLBSL | SMPDA | null | null | Blocked — historical snapshot unavailable |
| SAMAJ | GBLBS | null | null | Blocked — historical snapshot unavailable |
| SFCL | PFL | null | null | Blocked — historical snapshot unavailable |

## Exact evidence needed to reopen recovery

Obtain one of the following, with source, retrieval timestamp, response hash and provider terms retained:

1. A ShareHub licensed `/stocks` response captured while predecessor symbols were active, or a provider-supplied historical stock/security master export with effective dates.
2. A dated NEPSE security-list response/archive that includes predecessor symbols and numeric security IDs.
3. A third-party historical security master (e.g. Chukul/NepseAlpha/ShareSansar) with explicit dated symbol-to-security-ID fields and provenance.

For each recovered ID, require at least one dated observation during the predecessor's active trading interval and another boundary observation around suspension/merger. Require independent floorsheet/price-history corroboration before assigning validity intervals. A current snapshot alone is insufficient.

## Safety disposition

Priority 98 is closed as a completed source-discovery task with a documented blocker. Priority 97 remains **NOT CLOSED** until historical IDs and validity intervals are supported. Keep `stable_id=null` and `effective_date_verified=false` for unresolved predecessors. Do not join predecessor and successor OHLCV by ticker similarity or corporate-event date. Do not train on or backtest across an unverified identity splice.

## Reproducibility

- Repository audit and code search completed 2026-11-26.
- ShareHub API documentation reviewed 2026-11-26.
- No authenticated credentials were accessed or requested in this audit.
- No production API call was made and no external account access was assumed.


## 2026-11-26 project-owner scope decision — current scanning

The project owner subsequently instructed the scanner to use the **2026-11-25 current snapshot ID for each surviving successor equity** and to ignore former tickers in the current universe because those instruments merged/acquired into the successors. Accordingly, historical predecessor ID recovery is **not a blocker for current-universe scanning**. The seven current successor IDs are SLBSL 2804, NMLBBL 396, MATRI 694, SMATA 2761, SMPDA 2896, GBLBS 583 and PFL 236. See [CURRENT_UNIVERSE_SUCCESSOR_ID_POLICY_2026-11-26.md](CURRENT_UNIVERSE_SUCCESSOR_ID_POLICY_2026-11-26.md).

This owner decision changes the **scope/acceptance requirement**, not the historical evidence findings above: predecessor IDs remain unrecovered, predecessor validity intervals remain unverified, and historical OHLCV/floorsheet splicing remains prohibited. Current successor IDs must not be backfilled onto predecessor records. Historical continuity research remains unresolved but optional to the current scanner. All independent data-quality, calendar, source-provenance, rights and CI release gates remain applicable.
