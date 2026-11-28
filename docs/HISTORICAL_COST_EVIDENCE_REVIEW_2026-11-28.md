# Historical execution cost evidence review — 2026-11-28

Review only; no canonical rate promotion or production authorization.

| Component | Evidence | Limitation |
|---|---|---|
| Brokerage, effective 2024-05-14 | https://www.sharesansar.com/newsdetail/sebon-to-enact-revised-commission-rates-for-stockbrokers-implementation-begins-today-2024-05-14 | Reports 0.36/0.33/0.31/0.27/0.24 percent. Earlier reporting https://www.sharesansar.com/newsdetail/sebon-announces-10-reduction-in-stockbrokers-commission-rates-effective-jestha-01-2024-05-07 reports 0.306 percent for third slab. Original amended schedule and rounding unresolved. |
| DP transfer | https://www.sebon.gov.np/uploads/uploads/UUqlgCkhxAnGbqkZMirCcGEdtFnx4KBmNeQqdicw.pdf ; Schedule 14, printed page 555, amendment note 2069 (2013) | Parsed text specifies NPR 25 per transfer; target-page screenshot timed out. Effective-date and later amendments, buy/sell incidence and settlement grouping not certified. |
| DP operational grouping | https://www.ssl.com.np/depository-participant-dp-fees | Provider says NPR 25 per beneficial owner, stock, settlement ID; not a complete historical rule. |
| Regulatory fee | https://ssl.com.np/trading-commission-and-fees | Provider reports additional 0.015 percent equity transaction fee. Historical effective periods unverified; distinguish embedded commission allocation from additional transaction fee. |
| Prior tax regimes | https://www.nrb.org.np/contents/uploads/2026/05/Annual-Report-2024-25-English.pdf | Search extract indicates 5 percent >365 days and 7.5 percent <=365 days in FY 2023/24 and 2024/25. Full PDF retrieval exceeded size limit; not accepted for date-level schedule. |
| 2026 tax revision | https://www.sharesansar.com/newsdetail/capital-gains-tax-rates-reduced-decision-published-in-gazette-2026-09-22 | Secondary report 3.75 percent >365 days and 5 percent <=365 days. Gazette effective date and taxpayer scope need primary verification. |

Existing historical_fee_reference.py is a partial third-party reference, not a certified fee schedule. Preserve both existing scenario calculation paths. No source bytes or SHA-256 captured in this review. No invented dates, no automatic rate changes, no production eligibility. Next: obtain original SEBON amendment and Gazette/IRD texts; validate effective intervals, taxpayer category, rounding and settlement fee grouping; then integrate with historical simulator and verify independent net performance.
