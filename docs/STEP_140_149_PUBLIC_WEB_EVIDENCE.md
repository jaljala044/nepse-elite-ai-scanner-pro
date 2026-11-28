# Steps 140–149 — public-web evidence discoveries

1. Search NEPSE Alpha indexed BENH historical OHLCV and public export page.
2. Cross-check first observed BENH trade: NEPSE stockWisePrices on 15 Oct 2026 shows close 313.90 and 90 shares. Listing notice says listed 13 Oct and scheduled trading 14 Oct. The 14 Oct BENH absence is not proven without complete archive.
3. Capture Share Gyan OHLCV rows 13 and 17–20 Nov, and OHLC-only rows 23–24 Nov.
4. Cross-check 27 Nov: ShareSansar, Share Gyan and NEPSEDATA agree on open 800, high 840, low 771, close 785, volume 33,244.
5. Flag 18 Nov close mismatch: Share Gyan reports 856.4; NEPSEDATA close-only capture says 837.
6. Classify 25 Nov Share Gyan row as intraday snapshot at 12:05 Nepal time; exclude from EOD.
7. Flag 26 Nov Share Gyan summary as internally inconsistent: summary volume 27,640 but floorsheet page says no transaction data.
8. Add first-trade chronology gate requiring complete archive coverage and primary exchange evidence.
9. Correct merger candidates: BPW→SLBSL (1:0.8535; 7 Mar 2024), JALPA+KLBSL→MATRI (1:0.8834; 11 Jul 2024), MKLB→SMATA acquisition (1:1; effective 8 Jul 2024). All secondary-evidence candidates only.
10. Add source-conflict validators and an evidence inventory. No production promotion.

## Public sources
NEPSE Alpha: https://nepsealpha.com/search?q=BENH and https://nepsealpha.com/nepse-data/
NepView daily BENH history: https://nepview.com/explore/BENH
ShareHub BENH page: https://sharehubnepal.com/company/BENH
NEPSE Quant BENH broker/floorsheet summary: https://nepsequant.com/stocks/BENH/brokers
NEPSE Portfolio Tracker broker activity: https://nepseportfoliotracker.app/script/benh-beni-hydropower-project-limited/brokers
NEPSE stockWisePrices: https://www.nepalstock.com/stockWisePrices
ShareSansar: https://www.sharesansar.com/company/benh and https://www.sharesansar.com/sectorwise-share-price
Share Gyan: https://sharegyannepal.com/company/BENH/price-history/ ; https://sharegyannepal.com/company/BENH/ ; https://www.sharegyannepal.com/company/BENH/floorsheet/
ShareSansar bulk archive: https://omitnomis.github.io/ShareSansarScraper/
Hugging Face NEPSE dataset: https://huggingface.co/datasets/AnkitSanjyal/nepse-market-data

## BENH chronology
Listing date: 2026-10-13. Scheduled trading start: 2026-10-14. First observed official NEPSE stockWisePrices record: 2026-10-15 (O/H/L/C 273/313.9/273/313.9; volume 90). A complete 14 Oct floorsheet archive was not located, so first-ever trade date remains unverified.

## Conflicts and exclusions
18 Nov: Share Gyan/NepView/NEPSE Alpha close 856.4 vs NEPSEDATA close-only 837; quarantine the NEPSEDATA value. NEPSE Alpha open differs from Share Gyan/NepView and remains field-level conflict.
25 Nov: Share Gyan 12:05 snapshot is intraday; NepView provides completed EOD row 798/828.8/776/828.8, volume 65,798.
26 Nov: Share Gyan floorsheet page failed to show rows; NepView and NEPSE Quant independently report 27,640 shares. Do not treat page failure as zero trading.
27 Nov: five-source OHLC/close/volume agreement; research evidence only pending original file capture/hash and complete session provenance.
2–5, 13, 17–19 Nov: field-level open-price differences between NEPSE Alpha and other public sources; preserve source-specific values and do not silently choose one.

## Important limits
The rows in the companion JSON were manually transcribed from public indexed web results. They are not raw downloads, not a complete history and not production data. Primary merger notices/security IDs still need review. No production identity mapping is approved.
