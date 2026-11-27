# Candidate NEPSE index endpoint HAR capture

This adapter is for evidence collection only. The route shapes below were
found in third-party reverse-engineered references; they are not an official
NEPSE API contract.

## Candidate route families

- `POST /api/nots/graph/index/{id}` — candidate graph route.
- `GET /index/history/{id}` — candidate history route.

Third-party references associate graph IDs 51–67 with index/sub-index views.
The importer records whether an ID falls in that range but does not infer the
index name from the ID or assert that any route is live, official, final,
complete or historically stable.

## Capture workflow

1. Open the NEPSE site in a browser and use Developer Tools → Network.
2. Enable Preserve log, navigate to the requested index/sub-index, and capture
   the exact graph/history request and response.
3. Export HAR with response content. Keep the HAR local; it may contain
   authentication headers and cookies.
4. Identify the zero-based entry index. Import the request and response:

```bash
python backend/capture_official_index_har.py \
  --har /secure/local/path/nepse-index.har \
  --entry-index 0 \
  --source-id nepse-index-58 \
  --output-dir data/evidence/index
```

The importer stores the exact response bytes and SHA-256 via the generic
official-HAR capture adapter. For safe request reproduction it also stores
the request path, query parameters, method, selected non-sensitive headers,
request-body bytes/hash for JSON POST bodies, and the names of sensitive
headers redacted. It rejects credential-like query/body keys. It does not
persist the HAR archive or authentication header values.

## Evidence limits

- `route_contract_status=third_party_discovery_only` is intentional.
- HAR cannot attest TLS/hostname verification or prove the publisher.
- A captured HTTP 200 does not prove finality, complete history, pagination
  limits, or correct index identity.
- Compare the response dates with an independently verified NEPSE session
  calendar; report missing and unexpected sessions without filling gaps.
- Capture graph and history routes separately for each requested index.
- Keep sub-indices unavailable unless their own route/identity/history is
  independently reviewed.
- The output always has `evidence_gate_passed=false`,
  `promotion_allowed=false`, and
  `production_index_signals_allowed=false`.

No reverse-engineered route should feed index intelligence or market health
until the first-party frontend contract, TLS/source provenance, schema,
history depth, finality and calendar coverage have been independently
reviewed.
