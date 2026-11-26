# P4.12 — typed security lifecycle event ledger — 2026-11-26

## Purpose

The existing 281-equity coverage input uses `valid_from` as the first-trading-start date for the session-coverage gate. That date must not be conflated with:
- the merger's joint-business / joint-operations effective date;
- the NEPSE listing date of post-merger shares;
- the date NEPSE releases a security for trading;
- the first date an actual contract executes;
- the first date present in an OHLCV archive.

This batch adds a separate typed event ledger. It does not rewrite unknown first-trade dates into the coverage input.

## Reviewed events

| Symbol | Event date | Event | Evidence | Meaning |
|---|---|---|---|---|
| NMLBBL | 2024-03-13 | Merger joint transactions start | Merolagani notice | Business effective date; not a confirmed trade |
| NMLBBL | 2024-05-17 | Merger shares listed and trading released | Official NEPSE listing PDF | Primary listing/release event; first contract not certified |
| SMPDA | 2024-07-14 | Merger joint operations start | Merolagani announcement | Business effective date; not a confirmed trade |
| SMPDA | 2024-08-15 | Merger shares listed | Official NEPSE listing PDF | Primary listing event; first contract not certified |
| MATRI | 2024-08-12 | Merger-successor shares listed | Merolagani report of NEPSE action | Listing date separate from recorded 13 Aug first-trade/archive match |
| NLO | 1986-12-14 | Original listing date | ShareHub company metadata | Secondary metadata only; does not prove first execution |

## Primary records

### NMLBBL

The official NEPSE PDF dated 17 May 2024 says 13,377,643 shares resulting from the 1:1 merger were listed and trading was released. The merger joint transaction was announced for 13 March 2024. These are distinct events.

- Official NEPSE PDF: https://www.nepalstock.com/api/nots/security/fetchFiles?fileLocation=rita_listing%2F2024-05-17%2FNMLBBL_1715925622934.pdf
- Merolagani merger effective-date announcement: https://eng.merolagani.com/NewsDetail.aspx?newsID=100214

The project OHLCV archive first positive-volume row was previously observed on 19 May 2024 (864 shares). That is a project archive observation, not an independently authenticated first transaction. Keep NMLBBL `valid_from` blank until complete exchange floorsheet evidence or another authoritative first-execution record is captured.

### SMPDA

The merger joint operations date is 14 July 2024. The official NEPSE PDF for the post-merger shares is dated 15 August 2024 and is linked from the listing notice. The archive first positive-volume row was previously observed on 18 August 2024 (5,314 shares). This does not independently authenticate first execution.

- Official NEPSE PDF: https://www.nepalstock.com/api/nots/security/fetchFiles?fileLocation=rita_listing%2F2024-08-15%2FSMPDA_1723716902880.pdf
- Merolagani merger effective-date announcement: https://merolagani.com/AnnouncementDetail.aspx?id=54360
- ShareSansar listing notice: https://www.sharesansar.com/eventdetail/listing-shares-of-sampada-laghubitta-bittiya-sanstha-smpda-after-merger-2024-08-15

Keep SMPDA `valid_from` blank until the first actual contract and successor security identity are reconciled.

### MATRI

Merolagani reports that NEPSE listed the merger-successor shares on 12 August 2024. The existing 13 August coverage-input date represents the reported first trading/archive match. The ledger now preserves the two dates as different event types.

- https://eng.merolagani.com/NewsDetail.aspx?newsID=104854

### NLO

ShareHub metadata reports a listing date of 14 December 1986. The project archive starts on 26 March 2024 and contains only 43 rows through 30 September 2026. This is a sparse archive, not evidence that the instrument began trading in 2024. Listing date is not substituted for first executed trade.

- https://sharehubnepal.com/company/NLO

## Register changes

- Added `data/reference/nepse_security_lifecycle_events_2026-11-26.csv`.
- Updated only the explanatory notes for NMLBBL, SMPDA and NLO in the 281-row lifecycle coverage input.
- Kept all three `valid_from` values blank and evidence status `unverified`.
- Kept the current security IDs from the 26 November 2026 manifest: NMLBBL 396, SMPDA 2896, NLO 198, MATRI 694.
- No OHLCV data or trading-session calendar changed.

## Next evidence required

1. Obtain date-complete floorsheet contract records around 19 May 2024 for NMLBBL and 18 August 2024 for SMPDA, including the immediately preceding NEPSE-open dates.
2. Verify effective-dated security-ID continuity across both predecessor entities and the successor symbol.
3. For NLO, acquire complete floorsheet/market-session evidence or a trusted historical trading record; do not treat archive sparsity as zero-trade evidence.
4. Add event-level source retrieval timestamps, raw payload hashes and immutable source IDs when the original documents/data are captured. Current event ledger stores URLs and evidence classifications, not raw payload hashes.

## Safety decision

No first-trade dates are inferred from listing dates or archive boundaries. No canonical/training promotion, backtest admission, or BUY eligibility change is authorized by this batch.
