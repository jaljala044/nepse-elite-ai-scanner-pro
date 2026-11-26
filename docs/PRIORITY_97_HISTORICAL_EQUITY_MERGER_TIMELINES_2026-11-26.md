# Priority 97 — historical equity merger timeline evidence expansion (2026-11-26)

## Result

Added sourced joint-transaction start dates for six predecessor symbols to `data/reference/nepse_historical_identity_evidence_2026-11-26.json`.

| Predecessor symbol(s) | Successor | Joint-transaction start | Evidence |
|---|---|---:|---|
| BPW | Samudayik Laghubitta (SLBSL) | 2024-03-06 | ShareSansar merger/listing report |
| MMFDB, NLBBL | Nerude Mirmire Laghubitta (NMLBBL) | 2024-03-13 | ShareSansar merger/listing report |
| JALPA, KLBSL | Matribhumi Laghubitta (MATRI) | 2024-07-11 | ShareSansar merger-completion report; Merolagani announcement |
| MKLB | Samata Gharelu Laghubitta (SMATA) | 2024-07-08 | ShareSansar post-acquisition listing report |

## Evidence interpretation

- ShareSansar's 2024-05-17 report states that BPW and SLBSL commenced joint transactions on 24 Falgun 2080, and MMFDB/NLBBL commenced joint transactions on 30 Falgun 2080.
- Merolagani's MATRI announcement states that Kisan Laghubitta and Jalpa Laghubitta commence joint transactions under Matribhumi from 27 Ashad 2081; ShareSansar's 2024-07-11 notice independently reports merger completion effective that day.
- ShareSansar's 2024-08-02 report states that Samata Gharelu and Manakamana Smart commenced joint transactions on 24 Ashad 2081.

## Remaining limits

These dates identify the start of joint corporate operations. They do not, by themselves, establish:
- the last exchange trading date for each predecessor symbol;
- the first exchange trading date for the successor symbol;
- exact NEPSE security IDs and their validity intervals before/after the event;
- uninterrupted identity continuity or a permissible historical-price splice.

Accordingly, every affected JSON record continues to carry `stable_id: null` and `effective_date_verified: false`. No historical prices were spliced, no filenames or aliases were changed, and no raw OHLCV/floorsheet data was modified. This evidence does not authorize canonical identity promotion or model-training use.

## Source links

- https://www.sharesansar.com/newsdetail/after-successful-merger-shares-of-samudayik-laghubitta-and-nerude-mirmire-laghubitta-listed-in-nepse-2024-05-17
- https://www.sharesansar.com/newsdetail/joint-trading-of-kisan-laghubitta-and-jalpa-samudayik-laghubitta-shares-transactions-suspended-2024-07-11
- https://www.merolagani.com/AnnouncementDetail.aspx?id=54224
- https://www.sharesansar.com/newsdetail/after-successful-acquisition-share-of-samata-gharelu-laghubitta-listed-in-nepse-2024-08-02
