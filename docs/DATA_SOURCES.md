# NEPSE data-source register and collection plan

Updated: 2026-11-23. This register separates observed public interfaces from feeds that
need a provider account, a licence, or an exact endpoint supplied by the provider.

## Collection tiers

| Source | Data/use | Access status | Collector status |
|---|---|---|---|
| OmitNomis ShareSansarScraper | Historical daily OHLCV archive, latest session, symbols | Public JSON archive; unofficial ShareSansar-derived data | Verified JSON snapshot endpoints implemented |
| SamirWagle/Nepse-All-Scraper | Daily floorsheet CSV/JSON, sector-index CSVs, company list | Public GitHub Pages API and flat files | JSON endpoints plus latest 10 floorsheets and index CSV collector implemented |
| jaljala044/nepse-history-starter | User-maintained OHLCV imports and source records | Public GitHub repository at inspection time | GitHub raw-file collector implemented |
| jaljala044/nepse-smc-data | EOD prices, market indices, daily floorsheet, OHLCV charts and scanner packages | Public GitHub repository at inspection time | GitHub raw-file collector implemented |
| nepsepy / nepse-client / nepse-data-api | Market, prices, floorsheets, indices, history, company data | Unofficial clients/APIs; availability and exact endpoints vary by project | Configurable provider endpoint only; no guessed API paths |
| Chukul | Broker desk and broker-flow analytics based on floorsheet | No public developer API contract verified | Requires provider-authorized API/export or manual file import |
| ShareHub | Market, sector indices, historical charts, raw floorsheet and broker analytics | User-identified API; endpoint, licensing and auth terms still need provider confirmation | Endpoint/token configuration supported; requires provider-issued docs and authorization |
| Hamro Share | App advertises prices, floorsheet, charts and broker analysis | No public developer API contract verified | Requires provider-authorized API/export or manual file import |
| NEPSE Alpha | Public market page displays market/floorsheet information | No stable public developer API contract verified | Manual exports or provider-authorized endpoint only |
| nepse.link MCP | Pre-computed broker-flow summaries | User-identified MCP service; API schema, lag and coverage not independently verified | Configurable provider endpoint only after validating schema and terms |

## Run the raw collector

From the backend folder after installing requirements:

```bash
python collect_sources.py
```

Choose sources:

```bash
python collect_sources.py --source sharesansar_archive --source samirwagle_archive
python collect_sources.py --source jaljala_history_starter --source jaljala_smc_data
python collect_sources.py --source samirwagle_archive
```

For a provider-authorized endpoint, configure its exact URL and optional bearer token in
the deployment environment (never commit secrets):

- `CHUKUL_DATA_URL`, optional `CHUKUL_API_TOKEN`
- `SHAREHUB_DATA_URL`, optional `SHAREHUB_API_TOKEN`
- `HAMROSHARE_DATA_URL`, optional `HAMROSHARE_API_TOKEN`
- `NEPSEALPHA_DATA_URL`, optional `NEPSEALPHA_API_TOKEN`
- `NEPSEPY_DATA_URL`, optional `NEPSEPY_API_TOKEN`
- `NEPSE_CLIENT_DATA_URL`, optional `NEPSE_CLIENT_API_TOKEN`
- `NEPSE_DATA_API_DATA_URL`, optional `NEPSE_DATA_API_API_TOKEN`
- `NEPSE_LINK_DATA_URL`, optional `NEPSE_LINK_API_TOKEN`

The collector deliberately does not guess private app endpoints or bypass authentication.
ShareHub documents a bearer-token flow and IP allow-list; request a licence and provide
the server IP to the provider before configuring it.

## Data integrity rules

1. Store raw responses unchanged with retrieval time, source URL, content type and SHA-256.
2. Do not merge raw files directly into canonical price/floorsheet tables.
3. Parse each schema separately; record source session date separately from retrieval time.
4. Check symbol/date duplicates, OHLC bounds, volume, timezone, missing sessions and stale data.
5. Cross-check ShareSansar-derived figures against NEPSE-origin records where available.
6. Treat floorsheet buyer/seller broker codes as execution channels, not beneficial-owner identity.
7. Broker-flow summaries are derived measures; keep their source and aggregation window visible.
8. Do not use adjusted prices as raw prices. Corporate actions need their own adjustment ledger.
9. Do not enable automated collection schedules until permissions, rate limits, coverage and
   reconciliation tests are complete.

## Known source caveats

- ShareSansarScraper explicitly describes itself as an unofficial archive sourced from ShareSansar.
- SamirWagle's project says its daily scraper stores flat files and runs after market close.
- ShareHub's API is a licensed service with rate limits and server-IP allow-listing.
- nepsepy is an unofficial client; exchange-side changes can break it.
- Chukul's Broker Desk says it aggregates NEPSE floorsheet activity. A broker represents
  many clients, so broker-level flow cannot identify the underlying investor.
