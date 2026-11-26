# P4.11.2 mid-2026 first-trade boundary batch — 2026-11-26

## Scope

Four additional low-overlap 2026-start equities were reviewed against dated lifecycle notices / first-debut reporting and the pinned OHLCV archive boundary.

| Symbol | First-trade / first-positive-volume date | Archive first-row volume | Evidence tier |
|---|---|---:|---|
| PCIL | 2026-04-10 | 250 | ShareSansar commencement notice + archive match |
| SIPD | 2026-04-10 | 140 | ShareSansar commencement notice + archive match |
| SKHEL | 2026-03-29 | 80 | Merolagani first special pre-open transaction report + archive match |
| RLEL | 2026-03-29 | 190 | Merolagani first special pre-open transaction report + archive match |

## Source references

- PCIL: https://www.sharesansar.com/eventdetail/listing-ipo-share-of-palpa-cement-industries-limited-pcil-2026-04-09
- SIPD: https://www.sharesansar.com/index.php/eventdetail/listing-ipo-share-of-shikhar-power-development-limited-sipd-2026-04-09
- SKHEL / RLEL: https://www.merolagani.com/NewsDetail.aspx?newsID=124637

## Controls

- Dates are entered as first-trade / observed start dates, not listing dates inferred from archive files.
- PCIL and SIPD are supported by published commencement notices and matching first-positive-volume archive rows.
- SKHEL and RLEL have dated first special pre-open transaction reporting and matching archive rows.
- All evidence remains secondary-source/project-archive corroboration; raw contract-level floorsheets were not captured.
- No OHLCV data was mutated or synthesized; no canonical/training promotion is implied.

## Outcome

- 281 equity rows retained.
- 4 additional populated `valid_from` values.
- Expected lifecycle register coverage: 24/281 populated; 257 remain unverified.
- Full daily session completeness after first trade, corporate-action treatment, historical stable-ID intervals, row-level OHLCV provenance and liquidity remain separate gates.
