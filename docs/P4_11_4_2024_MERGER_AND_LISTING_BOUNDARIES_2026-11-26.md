# P4.11.4 — 2024 lifecycle and merger-boundary review — 2026-11-26

## Scope

Reviewed the 2024 archive-start candidates whose OHLCV files begin after the common 2024-03-04 collection boundary. This batch only populates dates where the successor/current instrument start is supported by dated listing or first-trade evidence.

## Added to lifecycle input

| Symbol | Current instrument start / first trade | Pinned OHLCV first row | Evidence |
|---|---|---|---|
| SARBTM | 2024-03-19 | 2024-03-19, 2,442 shares | ShareSansar explicitly reports first trading day; Merolagani listing notice dated 18 March; archive match |
| MATRI | 2024-08-13 | 2024-08-13, 1,391 shares | Merger-successor shares listed 12 August; NepseAlpha reports trading from 13 August; archive match |

Sources:
- SARBTM first-trading report: https://www.sharesansar.com/newsdetail/nepse-index-loses-624-points-in-todays-trading-session-sarbottam-cement-hits-positive-circuit-on-first-trading-day-2024-03-19
- SARBTM listing notice: https://eng.merolagani.com/AnnouncementDetail.aspx?id=53091
- MATRI trading-start report: https://nepsealpha.com/post/detail/5699/shares-of-matrubhuti-laguvitta-listed-on-nepse-trading-from-today
- MATRI merger listing report: https://www.sharesansar.com/newsdetail/after-successful-merger-between-jalpa-and-klbsl-shares-of-matribhumi-laghubitta-listed-in-nepse-2024-08-12

## Quarantined merger / archive discrepancies

### NMLBBL — do not infer from archive

- Merolagani and ShareSansar report the Nerude–Mirmire joint transaction under NMLBBL was scheduled to start 2024-03-13.
- ShareSansar reports merger shares listed on 2024-05-17; its company profile records operation date 2024-05-19.
- Pinned project OHLCV first positive-volume row is 2024-05-19 (864 shares).
- The 2024-03-13 joint-transaction date and 2024-05-19 archive boundary are not interchangeable. The first actual execution after the ticker/ID transition and the intervening coverage require raw floorsheet or exchange evidence. NMLBBL remains `UNKNOWN` in the lifecycle register pending this reconciliation.

Sources:
- https://eng.merolagani.com/NewsDetail.aspx?newsID=100214
- https://www.sharesansar.com/newsdetail/after-successful-merger-shares-of-samudayik-laghubitta-and-nerude-mirmire-laghubitta-listed-in-nepse-2024-05-17
- https://www.sharesansar.com/company/NMLBBL

### SMPDA — predecessor identity / successor symbol ambiguity

- Sadhana and Sabaiko began joint operations under Sampada on 2024-07-14.
- Merger shares were listed on 2024-08-15; NepseAlpha later reported listing/unfreezing on 2024-08-18.
- Pinned OHLCV first positive-volume row is 2024-08-18 (5,314 shares).
- SRAN's company profile reports an older IPO/first-trade date in 2020 for the predecessor lineage. This is not sufficient to assign the 2024 successor security's first execution or prove continuity of security ID. SMPDA remains `UNKNOWN` pending effective-dated identity and floorsheet reconciliation.

Sources:
- https://www.sharesansar.com/index.php/newsdetail/after-successful-merger-between-sabsl-and-sdlbsl-shares-of-sampada-laghubitta-listed-in-nepse-2024-08-15
- https://nepsealpha.com/post/detail/5718/shares-of-sampada-laguvitt-financial-institution-limited-are-listed-on-nepsenull
- https://sran.com.np/companies/smpda

### NLO — sparse historical trading is not a listing boundary

NLO's archive starts 2024-03-26 and contains only 43 rows through 2026-09-30. This is an archive/sparse-trading boundary, not a credible original listing or first-trade date. Preserve the separate sparse-trading review and keep the lifecycle start unknown.

## Outcome

- Two additional lifecycle starts populated.
- Lifecycle input remains 281 rows; combined populated `valid_from` count is expected to be 44/281.
- NMLBBL, SMPDA and NLO remain unverified rather than being filled from convenient archive dates.
- The 2024 review does not establish complete daily floorsheet/session coverage, predecessor-to-successor ID continuity, corporate-action price basis or row-level OHLCV provenance.
- No raw OHLCV mutation, no synthetic bars, no canonical/training promotion, and no BUY eligibility change.
