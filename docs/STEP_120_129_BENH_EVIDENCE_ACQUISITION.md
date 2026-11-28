# Steps 120–129 — BENH evidence acquisition and predecessor research

## Implemented steps
120. Document ShareHub historical API access prerequisite: Data API licence, allow-listed server IP and enabled price-history service. No credentials were present; no private endpoint was called.
121. Record Chukul chart acquisition result: browser-rendered chart page returned empty content; no candle rows admitted.
122. Capture ShareSansar BENH profile and dated listing/trading notices. Listing date is 2026-10-13; notice says trading commences 2026-10-14.
123. Record floorsheet acquisition state as NOT_ACQUIRED; the surfaced pages do not expose a verified historical BENH archive.
124. Store 22 real BENH daily close observations extracted from NEPSEDATA with source URL, capture date and raw excerpt SHA-256.
125. Keep close-only observations separate from OHLCV; cross-provider OHLCV reconciliation remains withheld.
126. Flag that the published close series begins 2026-10-15 although the ShareSansar listing notice says trading was to commence 2026-10-14. The first observed close is not asserted to be the first-ever trade.
127. Record BPW→SLBSL as a secondary candidate. An NEPSE-hosted merger notice PDF was located, but its scan was not text-verifiable; no effective date is admitted.
128. Record JALPA and KLBSL→MATRI as a secondary merger candidate; ShareSansar reports joint transaction began Ashad 27, 2081 and swap ratio 1:0.8834. Primary merger approval evidence is still required.
129. Preserve MKLB as its own NEPSE-listed identity from the NEPSE company-list PDF; do not invent a successor mapping.

## BENH close-only evidence
The captured public table at https://nepsedata.com/stock/BENH contains 22 closing prices from 2026-10-15 through 2026-11-27. The data file is `data/evidence/benh/2026-11-28/close_only.json`. The SHA-256 is for the exact extracted date/close text excerpt, not a downloaded raw HTML response.

No open/high/low/volume/trade count fields were captured in that table. This is a research-only close series, not OHLCV, not floorsheet, not a complete all-time history, and not eligible for production signals.

## Source access blockers
- ShareHub documents a daily price-history endpoint, but access requires a licensed Data API account, IP allow-list and enabled service. No API credentials were supplied.
- Chukul's chart and floorsheet pages returned empty rendered content in this capture.
- ShareSansar company profile is readable; historical chart and historical floorsheet rows were not extracted.
- No BENH floorsheet archive or coverage-completeness proof was acquired.

## CI repair
The Steps 110–119 provider-conflict test had an invalid Chukul fixture: it included a generic `close` field that the adapter correctly prioritized over `closePrice`. The fixture now uses Chukul-only aliases so the intended mismatch is actually exercised.

All identity records remain candidates/unresolved. No security IDs, effective-dated joins, first-trade verification or production admission are approved by this batch.
