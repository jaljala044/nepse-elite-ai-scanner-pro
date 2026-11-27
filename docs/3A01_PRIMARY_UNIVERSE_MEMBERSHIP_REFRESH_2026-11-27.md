# 3A.01 — Primary active-equity membership source refresh

**Audit date:** 2026-11-27  
**Scope:** Determine whether current public evidence can certify the complete active ordinary-equity universe for the market-wide scanner.  
**Disposition:** **Blocked — no sufficiently fresh, independently authenticated primary membership snapshot was established.**  
**No production universe or canonical manifest was changed.

## Findings

### 1. Official NEPSE public stocklist

The official NEPSE stocklist page was publicly indexed with an explicit as-of timestamp of **2026-10-15 15:00**:

- URL: https://www.nepalstock.com.np/stocklist
- Search/index evidence retrieved 2026-11-27: https://www.nepalstock.com.np/stocklist
- Age at this audit: 43 calendar days.
- The page is an official exchange source, but its available timestamp is too old to certify membership as of 2026-11-27.
- The page's visible quote/traded-volume display is not itself a complete effective-dated lifecycle registry. A symbol's absence from a page snapshot must not be interpreted as delisted, suspended, or not listed without source semantics.

The official alternate catalogue page was indexed with an older explicit timestamp of **2026-09-24 15:00**:

- URL: https://www.nepalstock.com.np/en/catalogue
- Search/index evidence retrieved 2026-11-27: https://www.nepalstock.com.np/en/catalogue
- Age at this audit: 64 calendar days.
- This does not improve the date coverage of the official stocklist.

The public page was not available as readable line-oriented HTML through the web reader, and an attempted browser inspection of its underlying network/API request did not start because the browser automation service reported an unavailable wallet balance. No endpoint, request payload, or API schema is therefore claimed or inferred in this audit.

### 2. Current secondary-provider page is not a primary registry

NepseAlpha's traded-stocks page was indexed on 2026-11-27:

- URL: https://www.nepsealpha.com/traded-stocks
- Its page explicitly describes its table as **only actively traded stocks**.
- The indexed page shows 284 active-traded entries, compared with 281 symbols in the project's 2026-11-26 candidate manifest.
- These counts have different source dates and scope semantics. The three-count difference is **not** a proven three-symbol add/remove list. The page does not, by itself, establish complete listed-equity membership, suspended-but-listed securities, effective dates, or official active status.
- It is useful as a secondary discrepancy signal only; do not replace the 281-symbol manifest or amend it from this count alone.

### 3. The 2026-11-25 security-ID snapshot is a current catalogue observation, not an authenticated historical registry

The repository contains `data/reference/nepse_security_id_snapshot_2026-11-25.csv` and its 281-symbol crosswalk. The crosswalk reports:

- 281/281 candidate symbols matched to a current snapshot security ID.
- 281/281 matched snapshot rows carry active status `A`.
- 0 current symbol/ID mismatches in that crosswalk.
- 281/281 candidate symbols have an OHLCV file-presence flag.

However, the repository's own successor-ID policy identifies the snapshot as a **third-party/current catalogue artifact** and explicitly says it does not independently certify upstream exchange origin, complete equity membership, or all instrument classifications. The snapshot's 573 rows are a mixed-instrument catalogue, not an equity-only membership response. The crosswalk proves consistency against that snapshot, not independent exchange authority.

Relevant repository evidence:
- `docs/EQUITY_SECURITY_ID_CROSSWALK_AND_LIFECYCLE_COVERAGE_2026-11-26.md`
- `docs/CURRENT_UNIVERSE_SUCCESSOR_ID_POLICY_2026-11-26.md`
- `docs/P4.25_HISTORICAL_IDENTITY_READINESS_AND_RUNTIME_GATES_2026-11-26.md`

Lifecycle coverage is still materially incomplete: the P4.25 audit records 44/281 lifecycle start dates, all secondary, 237 undated and zero primary dated starts. The later crosswalk report documents nine secondary first-trade/archive matches and 272 unknown starts. Neither count establishes exchange-authenticated effective dates.


### 4. Additional current secondary catalogue cross-checks

Two further public secondary pages were indexed on 2026-11-27:

- HamroShare's NEPSE listings page describes **955 securities across 15 sectors**, with **560 marked Active**. It presents a broader all-securities count than NepseAlpha's 652-entry listed-company table, but the retrieved preview does not establish a complete raw export, exact instrument taxonomy, exchange authentication, or effective-dated lifecycle. Treat 955/560 as a provider-specific discrepancy signal only.
- NEPSEDATA's listed-companies page carries a **2026-11-26** snapshot label and displays market snapshot fields (close, point/percentage change, market cap, turnover and volume). This is useful for current quote cross-checking, not proof of the complete listed-security registry or inactive/suspended lifecycle.

The 652 (NepseAlpha), 955/560 (HamroShare) and 573-row project security snapshot are not directly comparable without each provider's full raw rows, instrument taxonomy, inclusion rules and as-of semantics. Their count differences must not be converted into inferred additions, removals or active-equity totals.

Sources:
- https://hamroshare.com.np/nepse/stocks
- https://nepsedata.com/stock/companies/


### 5. Official macro-statistical cross-check (NEPSE figures reproduced by Nepal Rastra Bank)

Nepal Rastra Bank's *Current Macroeconomic and Financial Situation* report for the first month of FY 2026/27 reproduces NEPSE-sourced listing statistics for **mid-August 2026**:

- **305 listed companies** in total.
- Sector breakdown: 133 BFIs and insurance, 111 hydropower, 31 manufacturing/processing, 9 hotels, 7 investment, 4 trading and 10 others (sum: 305).
- The report separately says 9.59 billion shares were listed and describes securities listed during the month, distinguishing ordinary shares from bonus shares.

This is a valuable official statistical cross-check with a stated reference date, but it counts **companies**, not the scanner's required one-row-per-security ordinary-equity universe. It does not provide the symbol-level list, security IDs, active/suspended/delisted status, or effective dates. Therefore 305 must not be compared as if it were a 305-symbol equity manifest, and it cannot authorize adding/removing any candidate symbols.

Source: Nepal Rastra Bank, *Current Macroeconomic and Financial Situation ... one month of data of 2026/27*, https://www.nrb.org.np/contents/uploads/2026/09/Current-Macroeconomic-and-Financial-Situation-English-Based-on-One-Month-data-of-2026.27-3.pdf (Capital Market, paragraphs 65–68; figures sourced to NEPSE).

## Evidence comparison

| Source | Latest explicit observation | Scope stated by source | Membership authority for 2026-11-27 |
|---|---|---|---|
| NEPSE `/stocklist` | 2026-10-15 15:00 | Official public stocklist / quote display | Official but stale; insufficient for current certification |
| NEPSE `/en/catalogue` | 2026-09-24 15:00 | Official public catalogue / quote display | Older; insufficient |\n| NEPSE figures reproduced by NRB | Mid-August 2026 | 305 listed companies by sector | Official statistical aggregate; not a symbol-level equity registry |
| NepseAlpha `/traded-stocks` | Indexed 2026-11-27 | Only actively traded stocks | Secondary and narrower than complete listed-equity universe |
| Project 2026-11-25 security snapshot | 2026-11-25 | 573-row mixed-instrument current catalogue snapshot | Secondary current-snapshot crosswalk; not an authenticated primary registry |\n| HamroShare listings | Indexed 2026-11-27 | 955 securities; 560 marked Active | Secondary provider-specific count; raw taxonomy/lifecycle not verified |\n| NEPSEDATA listed companies | 2026-11-26 snapshot label | Current market snapshot fields | Quote cross-check only; not a complete lifecycle registry |
| Project 2026-11-26 equity candidate manifest | 2026-11-26 | 281 equity candidates from NepseAlpha | Working candidate universe only |

## Decision and scanner impact

1. Retain the 281-symbol list as the **development candidate universe**; do not relabel it as the complete active NEPSE equity universe.
2. Do not infer that the 284-versus-281 count difference identifies exactly three additions or removals.
3. Do not treat a current status `A` as proof of a complete, effective-dated listing/suspension/delisting history.
4. Do not use missing traded-stock entries as proof of delisting or suspension.
5. Keep `membership_authoritatively_verified=false` and `promotion_allowed=false` until a raw, dated primary NEPSE/SEBON registry or equivalent authenticated exchange response is captured, hashed, independently parsed, and classified by instrument type and lifecycle.
6. Preserve the canonical reviewed-row manifest as empty. This membership audit does not alter any OHLCV records, candidate symbols, security IDs, or runtime eligibility.

## Next evidence action

Acquire a fresh primary-source security master from NEPSE (or an authenticated NEPSE/SEBON/CDSC registry with documented scope), preserving the raw response bytes, request URL/method, retrieval timestamp, as-of/effective date, schema, instrument-type and active/delisted/suspended fields, and SHA-256. Then reconcile all rows against the 281 candidates and report exact missing, additional, non-equity, inactive, ambiguous and duplicate records. Until this evidence exists, the universe gate remains blocked.

## Public source references

- NEPSE stocklist: https://www.nepalstock.com.np/stocklist
- NEPSE catalogue: https://www.nepalstock.com.np/en/catalogue\n- NRB report reproducing NEPSE listing statistics: https://www.nrb.org.np/contents/uploads/2026/09/Current-Macroeconomic-and-Financial-Situation-English-Based-on-One-Month-data-of-2026.27-3.pdf
- NepseAlpha actively traded/listed securities: https://www.nepsealpha.com/traded-stocks\n- HamroShare listings: https://hamroshare.com.np/nepse/stocks\n- NEPSEDATA listed companies: https://nepsedata.com/stock/companies/
