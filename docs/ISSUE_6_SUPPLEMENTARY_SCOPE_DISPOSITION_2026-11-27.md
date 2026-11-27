# Issue #6 — supplementary instrument follow-up disposition

Date: 2026-11-27

## Mutual-fund candidate count

The checked-in `data/reference/nepse_target_universe_candidates_2026-11-26.csv` was parsed row by row:
- 325 total candidate rows.
- 278 rows classified as Equity in the rendered-list snapshot.
- 47 rows classified as Mutual Fund.
- No additional count or lifecycle claim is inferred from those rendered-list classes.

The separate versioned equity candidate manifest contains 281 rows. The three supported additions (NESDO, ULBSL and YMHL) remain equity additions; they do not change the 47-row mutual-fund candidate count. Mutual funds remain supplementary and excluded from the equity scanner.

## NICEF one-pass follow-up

NICEF is a closed-end mutual fund, security ID 9357, listed 2026-11-04 with 100,000,000 units at NPR 10. ShareSansar reported that trading was expected to begin Thursday 2026-11-05. MeroLagani's announcement confirms the listing but not an executed trade.

A bounded follow-up pass reviewed:
- ShareSansar listing announcement.
- MeroLagani listing announcement.
- Asian Securities' 2026-11-05 listing-notice index.
- ShareSansarScraper's NICEF history endpoint (previously returned HTTP 404).
- NepseAlpha's public historical price-export page.
- The 2026-11-05 market report (confirms the session, but contains no NICEF-specific execution evidence).

No source in this pass yielded a dated NICEF executed trade or a complete NICEF OHLCV row. The actual first-trade date and first OHLCV remain null. The structured lifecycle record preserves this explicitly.

## Scope decision

- Close the exact-count verification requirement for supplementary mutual-fund candidates at the observed 47-row inventory level; do not claim 47 is an independently verified complete exchange universe.
- Close the NICEF follow-up after this bounded search pass. Do not continue chasing this supplementary gap.
- Keep NICEF in the instrument/lifecycle registry and outside the equity scanner.
- Do not synthesize OHLCV, zero-volume candles, a first-trade date, or a no-trade label.
- Missing supplementary mutual-fund data and unverified fund counts do not block equity coverage, scanner validation, or web/app delivery.

The 281-row equity manifest remains a secondary-provider candidate manifest. This addendum does not promote it to exchange-authoritative status or resolve outstanding effective-dated equity identity/lifecycle evidence.
