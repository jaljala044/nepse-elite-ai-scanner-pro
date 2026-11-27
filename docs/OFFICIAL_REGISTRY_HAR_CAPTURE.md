# Official NEPSE/SEBON browser HAR evidence import

Use this adapter when the official site is reachable in a browser but the
automated retrieval environment cannot fetch the response. It extracts one
selected HTTP 200 response from a HAR 1.2 archive and writes the exact response
body into the existing content-addressed evidence directory.

## Capture procedure

1. Open the official NEPSE or SEBON page in a browser with developer tools.
2. In the Network panel, enable **Preserve log** and reload the page.
3. Identify the exact official JSON registry or PDF request. Do not select
   analytics, authentication, advertising, or unrelated requests.
4. Export the network log as HAR **with response content**.
5. Keep the HAR local. Browser HAR files can contain cookies, bearer tokens,
   personal identifiers and other sensitive request headers. Do not commit or
   share the HAR file.
6. Identify the zero-based entry index in `log.entries`, then run:

```bash
python backend/capture_official_har.py \
  --har /secure/local/path/nepse-capture.har \
  --entry-index 0 \
  --source-id nepse-security-registry \
  --output-dir data/evidence/registry
```

Use a distinct source ID for each source/request capture. The importer stores
only the selected response bytes and a metadata sidecar; it records the SHA-256
of the original HAR but deliberately does **not** archive the HAR itself, to
avoid copying browser credentials into the evidence store.

## Evidence limits

- Only HTTPS URLs on the exact NEPSE/SEBON host allowlist are accepted.
- Only HTTP 200 JSON object/array or PDF responses are accepted.
- Exact response bytes, response SHA-256, byte count, source URL, HTTP status,
  content type and HAR-provided timestamp are retained.
- The HAR timestamp is operator/browser capture metadata, not an independently
  trusted exchange timestamp.
- HAR does not establish TLS certificate validation, hostname validation,
  publisher identity, response completeness, historical effective dates, or
  official schema semantics. Those statuses remain explicitly unverified.
- The adapter does not infer security IDs, symbols, sector labels, effective
  dates or universe coverage. It never admits sector membership or enables
  production sector signals.
- Review the selected request/response manually and independently validate
  source provenance before running the schema profiler and membership manifest
  audit. Do not use an authenticated/private endpoint or export secrets.

## Reproducibility

The content-addressed response filename is based on SHA-256 of the exact
response body. The HAR SHA-256 binds the import metadata to the original local
capture, but the original HAR must remain in a controlled operator environment
if an auditor needs to reproduce the selected entry. Do not publish that HAR
if it contains credentials; create a sanitized, documented evidence copy only
under an approved secrets-handling procedure.
