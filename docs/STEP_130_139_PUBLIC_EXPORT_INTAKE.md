# Steps 130–139 — no-API public/export evidence intake

This batch is designed for an account that has advanced-feature subscriptions but no provider API credentials. It does not call private endpoints, bypass logins, or require paid API access.

## Ten implemented steps
130. Define API-independent intake: public page capture and user/provider CSV or JSON exports.
131. Add ShareHub, Chukul and ShareSansar column profiles for daily OHLCV exports.
132. Normalize provider aliases and compare values across distinct providers; single-provider observations are not mislabeled as corroborated.
133. Create immutable import manifests with SHA-256, byte count, provider, symbol, filename, capture time and access mode.
134. Validate OHLCV relationships, numeric values and duplicate symbol/session rows; quarantine rejected rows.
135. Keep close-only records in a separate schema that can never satisfy OHLCV admission.
136. Import floorsheet CSV rows into daily trade count, volume, turnover and broker-number summaries; broker numbers remain execution channels, not beneficial owners.
137. Compare observed sessions with a supplied expected-session calendar and report gaps without filling them.
138. Verify first-trade claims only when primary exchange evidence and an archive with explicit completeness bounds cover the scheduled session.
139. Add an evidence-based identity intake and a no-API readiness report; identity candidates remain unapproved.

## How data can enter without API credentials
- Export or download a CSV/JSON file from a provider page/account if the provider makes that export available to your subscription.
- Save the original file unchanged. The importer records its SHA-256 before normalization.
- Provide provider name, symbol, capture timestamp with timezone, and source page URL where available.
- For pages that only show chart data, capture/export the actual rows if the UI permits it; a screenshot alone is not OHLCV data.
- If a site does not expose downloadable rows, mark it ACCESS_BLOCKED/NOT_ACQUIRED. Do not scrape around access controls or manufacture candles.

## Limits and controls
- CSV intake is implemented; XLSX workbook parsing and browser automation are not part of this batch.
- A source export is third-party distributed data, not an independently verified NEPSE exchange record.
- A matching pair of provider rows is corroboration, not proof of archive completeness.
- A broker code identifies a transaction channel, not ownership or manipulation.
- First-trade date verification requires a primary exchange source and a complete floorsheet archive spanning the scheduled first session.
- All outputs are research-only. No production signals, identity joins, or backtest promotion are enabled.

## Test
Run from backend: `python -m unittest discover -s tests -p 'test_p4_38_public_export_intake.py'`.
