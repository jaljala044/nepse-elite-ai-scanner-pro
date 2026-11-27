# ShareSansar-derived archive capture — 2025-07-28

- Retrieved from GitHub repository `OmitNomis/ShareSansarScraper`.
- Original daily CSV path: `docs/Data/2025_07_28.csv`.
- Original file blob SHA (Git object): `28b5edf90ea5ebfe7e419c5162eedd0f30a9ce82`.
- Source URL: https://omitnomis.github.io/ShareSansarScraper/Data/2025_07_28.csv
- Archive documentation: https://github.com/OmitNomis/ShareSansarScraper/blob/master/README.md
- Archive provenance: its README says the daily CSV is scraped from ShareSansar's `today-share-price` table. This is a ShareSansar-derived capture, not an independent sixth-party source.
- Daily file contains 321 data rows (322 lines including header); all five target symbols were present.
- Field names retained exactly from the daily CSV: `Open`, `High`, `Low`, `Close`, `LTP`, `VWAP`, `Vol`, `Turnover`, `Trans.`.
- The source's `Close`, `LTP`, and `VWAP` are retained as separate fields. No assumption is made that these are interchangeable.
- Retrieval timestamp: 2026-11-27 (repository fetch during this task).
- SHA-256 was not computed in this capture environment; the Git blob SHA is recorded instead and is not represented as SHA-256.
- The archive is explicitly unofficial and disclaims affiliation with ShareSansar or NEPSE.

## Five target rows

See `target-five-rows.csv` for the extracted rows. The full original CSV is preserved as `daily-board.csv`.

## Integrity follow-up — 2026-11-27

The preserved daily-board.csv and upstream docs/Data/2025_07_28.csv were fetched as base64 and matched exactly after removing transport whitespace. Both returned Git blob `28b5edf90ea5ebfe7e419c5162eedd0f30a9ce82`. SHA-256 of decoded existing file bytes: `36730b61430c2a42f7f1e33231c6b1b39e58037acc27bf24a62ac40ffed7a37d` (54019 bytes). SHA-256 implementation checked against standard abc test vector. This is a retrospective hash of the preserved matching bytes, not a newly captured HTTP response or proof of data accuracy.
