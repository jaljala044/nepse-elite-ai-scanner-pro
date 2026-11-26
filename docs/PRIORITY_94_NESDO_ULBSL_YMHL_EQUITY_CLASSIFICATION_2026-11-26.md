# Priority 94 — NESDO, ULBSL and YMHL equity classification evidence

Date reviewed: 2026-11-26

## Scope

Resolve the three symbols that appear in the 281-symbol provisional OHLCV coverage set but were absent from the 278-symbol equity candidate list. This review is restricted to listed ordinary equities. Mutual funds and debentures are excluded.

## Findings

| Symbol | Company | Sector | Supporting evidence | Conclusion |
|---|---|---|---|---|
| NESDO | Nesdo Sambridha Laghubitta Bittiya Sanstha Limited | Microfinance | ShareSansar company profile identifies symbol NESDO, sector Microfinance, 2,913,375 listed shares, and a current traded-price record. ShareSansar also reports its bonus shares listed on NEPSE. | Listed company equity; not a mutual fund. |
| ULBSL | Upakar Laghubitta Bittiya Sanstha Limited | Microfinance | ShareSansar company profile identifies symbol ULBSL, sector Microfinance, 1,061,482 listed shares, and a current traded-price record. | Listed company equity; not a mutual fund. |
| YMHL | Yambaling Hydropower Limited | Hydropower | ShareSansar company profile identifies symbol YMHL, sector Hydropower, 7,000,000 listed shares, and a current traded-price record. ShareSansar's listing notice states NEPSE listed the IPO shares on 2026-06-19 and trading commenced 2026-06-22. | Listed company equity; listing and trading start dates evidenced. |

## Sources

1. NESDO — ShareSansar company profile: https://www.sharesansar.com/company/NESDO
2. NESDO — ShareSansar bonus-share listing notice: https://www.sharesansar.com/newsdetail/1425-bonus-shares-of-nesdo-sambridha-laghubitta-listed-in-nepse-2025-06-03
3. ULBSL — ShareSansar company profile: https://www.sharesansar.com/company/ULBSL
4. YMHL — ShareSansar company profile: https://www.sharesansar.com/company/YMHL
5. YMHL — ShareSansar NEPSE IPO listing notice: https://www.sharesansar.com/eventdetail/listing-ipo-share-of-yambaling-hydropower-limited-ymhl-2026-06-19
6. NEPSE stock list: https://www.nepalstock.com.np/stocklist (search result snapshot crawled 2026-10-15 included NESDO, ULBSL and YMHL among traded symbols).

## Interpretation and limits

- Microfinance is a business sector, not a mutual-fund instrument type. NESDO and ULBSL represent company shares and therefore belong in an equity universe when the universe includes listed ordinary shares across all equity sectors.
- YMHL is a listed hydropower company; its NEPSE listing date and first trading date are explicitly documented.
- These sources establish company identity, equity/share classification, listing and observed trading. They do not independently establish every historical effective date, historical stock-ID mapping, or all lifecycle transitions.
- The 2026-11-25 security snapshot's IDs (NESDO/8041, ULBSL/8063, YMHL/9342) remain snapshot-level mappings pending a dated, complete security-master history.
- No canonical universe file, raw OHLCV, or floorsheet records were changed in this review. No model-training approval is implied.

## Recommended disposition

Classify NESDO, ULBSL and YMHL as **equity inclusion candidates supported by approved-provider evidence**. Add them to the canonical active-equity universe only after the symbol-to-security-ID mappings and effective dates are reconciled against the source snapshot and the universe's as-of date. If the project definition excludes any equity sector, record that exclusion explicitly; do not exclude microfinance merely because it is a microfinance sector.
