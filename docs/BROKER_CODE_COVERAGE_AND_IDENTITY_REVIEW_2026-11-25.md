# NEPSE broker-code coverage and identity review — 2026-11-25

## Summary

The 2026-11-24 source sample contains **91 distinct numeric broker codes** across buyer and seller columns. Every one of those 91 codes is present as a matching **CM No.** in the current CDSC List of Clearing Members, and the MeroLagani Listed Brokers table also shows these numeric broker numbers.

- Samir/Mero capture: 52,369 contracts, 104,738 buyer/seller party observations.
- SocrateAI capture: 52,387 contracts, 104,774 buyer/seller party observations.
- Unique observed broker codes in either file: **91**.
- Missing code numbers against the current CDSC clearing-member directory: **0**.
- Ambiguous or unresolved historical identity periods remain: **not yet measured**.

This is a **code-directory coverage pass**, not a license to treat all 91 historical broker-code mappings as verified over all years. The current CDSC directory is a present-day clearing-member snapshot; it does not provide a complete effective-dated history of each member's name, merger, suspension, branch, code reassignment or membership status. A broker code may therefore be present and nameable today but require a historical alias record for older floorsheet rows.

## Sources

1. [CDSC — List of Clearing Members](https://cdsc.com.np/listofclearingmember) is the primary current directory reviewed. It exposes Clearing Member Name and CM No.; all 91 observed source codes have an exact CM No. match. Its list contains CM No. 55 as well, which was not observed in the 2026-11-24 sample. The directory identifies clearing members; it does not, on its own, document all historical NEPSE broker-number/name effective dates.
2. [MeroLagani — Listed Brokers](https://eng.merolagani.com/BrokerList.aspx) is a secondary broker directory. Its current search-indexed result shows the numeric broker numbers and the names used in the broker list.
3. [SEBON — Stock Brokers](https://sebon.gov.np/intermediaries/stock-brokers) is the regulator's broker directory. It lists broker legal names and contact details, but the current page does not expose a NEPSE broker number in the extracted directory rows.
4. [SEBON — Investors' Handbook / Annexure 3](https://www.sebon.gov.np/uploads/uploads/8vjyqESdkGGheki88AA5NS2yremG1FMX8VpMw0ZO.pdf) provides a historical stockbroker table with a B.N. (broker number) column. It is older and cannot be used as the current name register without further history review.

## Two name-history cases that must not be collapsed

### Broker code 8

- Current CDSC and MeroLagani directories use **Brilliant Securities Pvt. Ltd.**
- The current MeroLagani directory also shows an \`8_RWS\` regional branch entry under the legacy Ashutosh Brokerage & Securities name. The company website and current broker-directory results describe Brilliant as the successor/current name for broker 8.
- A precise effective date for the rebrand was not established by the source material captured in this review.
- Keep \`Ashutosh Brokerage & Securities\` as a historical/legacy alias candidate for code 8; do not infer an exact effective-from date.

Sources: [CDSC directory](https://cdsc.com.np/listofclearingmember), [MeroLagani broker list](https://eng.merolagani.com/BrokerList.aspx), [Brilliant Securities company history](https://www.brilliantsecurities.com.np/about-us).

### Broker code 91

- The current CDSC directory calls code 91 **Citizens Share Broker Limited**.
- MeroLagani's broker list and broker floorsheet pages still display **CBIL Securities Ltd.** in some indexed content.
- The company's financial statement says its 2nd Special General Meeting resolved the name amendment on **2025-01-21**, and the Office of the Company Registrar recorded the change on **2025-04-01**.
- The company is therefore the same code-91 broker with a documented name change, not two separate broker entities. For source observations, preserve the name actually shown by that source and map the alias only over a supported effective period.

Sources: [CDSC directory](https://cdsc.com.np/listofclearingmember), [Citizens Share Broker audited financial statements](https://citizensbroker.com/public/assets/reports/68b435e995ac4.pdf), [MeroLagani broker floorsheet for code 91](https://eng.merolagani.com/BrokerFloorsheet.aspx?code=91).

## Registry artifact

\`data/reference/broker_code_crosswalk_candidates_2026-11-25.csv\` contains one row for each of the 91 observed codes, with:
- the source code and matching CDSC CM No.;
- the current CDSC directory name;
- an alias/history note where a name transition is known;
- flags showing whether the code was observed in each pinned 2026-11-24 sample;
- an explicit non-verified candidate status and retrieval date.

The file intentionally does **not** create \`BrokerIdentityLink(status="verified")\` entries. Name/code coverage is not enough to assign a stable broker legal-entity ID across every past trading date. The next stage must add source name observations and effective-dated entity-name records, with primary documentary evidence for each change or reassignment.

## Coverage caveats

- Broker source codes identify the broker execution channel, not beneficial owners or the underlying client.
- One contract yields a buyer-side and seller-side observation; do not sum both sides when calculating total market turnover.
- The 91-code union is the set observed in this one date, not proof that 91 brokers are active in every historical session.
- Code 55 is present in the CDSC directory but not observed in this day's two files; that absence alone does not imply inactive, suspended or delisted.
- Preserve raw numeric broker codes as strings and keep their original source-file lineage.

**Decision:** 91/91 code-number coverage against the current CDSC clearing-member directory; broker-entity resolution remains candidate-only until effective-dated source and legal-name history is completed.
