# 3A.01 — Security-master acquisition path and external access gate

**Audit date:** 2026-11-27  
**Disposition:** **Source path identified; acquisition blocked by licensed access and missing primary raw capture.**  
**Scope:** Add an actionable acquisition specification for the complete active-equity universe without treating a third-party current feed as an official NEPSE registry.

## Best documented acquisition route found

ShareHub's published NEPSE Data API documentation identifies this security-list endpoint:

`GET https://sharehubnepal.com/data/api/v1/nepse-data/security/all/mini`

The endpoint is described as returning every security with:
- security ID
- NEPSE ID
- symbol
- slug
- name
- logo
- sector
- active flag
- promoter flag

Documentation:
https://sharehubnepal.com/data/nepse-data-documentation/

Relevant documentation sections:
- Authentication and access requirements: lines 27–40, 117–163.
- Security-list endpoint and fields: lines 562–566.
- Sales/access path: lines 871–882.

The API documentation says every call requires a ShareHub Data API account, an enabled service on the licence, and an allow-listed server IP (unless test mode is enabled by ShareHub). It also documents Bearer-token and server-side API-key authentication. No credentials, licence or IP allow-list are available in this project session, and no authenticated call was attempted.

### Important limitation

The documented security-list schema does **not** promise:
- an as-of/effective timestamp for each security row;
- a complete listing, suspension, delisting or trading lifecycle;
- ordinary-equity instrument classification in the listed mini schema;
- an exchange-authenticated raw payload or direct NEPSE source chain.

Therefore, even a successful ShareHub response would be a dated third-party current-security snapshot, not by itself a primary NEPSE membership certificate. It would be useful as an independent current cross-check and ID reconciliation source. The existing 2026-11-25 snapshot remains a prior point-in-time observation only.

## Public NEPSE API path

The repository's earlier source audit and public NEPSE client references identify separate company-list and security-list routes, including:
- `/api/nots/company/list`
- `/api/nots/security?nonDelisted=true`

The public NEPSE endpoints were not readable through the web retrieval channel during this audit. Earlier project testing recorded unauthenticated 401 responses. This report does not claim that those routes are currently public, nor does it infer undocumented request headers, token generation, or endpoint semantics.

A public client documentation page describes `getSecurityList()` as the list of all non-delisted securities, and `getCompanyList()` separately as the list of all listed companies:
https://nepseclient.readthedocs.io/en/latest/api/client.html

This is third-party client documentation, not an official NEPSE API contract. A fresh raw response and source authentication evidence are still required.

## Secondary discrepancy signal

NepseAlpha's public page is indexed with two different table scopes:
- 284 entries in the active-traded stock table; the page explicitly says only actively traded stocks are shown there.
- 652 entries in a separate listed-company table with Status, Sector and Instrument columns; the indexed preview exposes only the first 10 rows, not the full export.

Source:
https://www.nepsealpha.com/traded-stocks

This is useful for discrepancy discovery but is not primary exchange evidence. The 284 and 652 counts must not be interchanged or interpreted as a complete current ordinary-equity universe without acquiring and hashing all rows and documenting the provider's field definitions. The 284 count is not proof of 3 specific additions to the project's 281 candidates.

## Acquisition specification

If project owner provides an authorized ShareHub licence/API key and allow-listed server environment, or obtains an official raw NEPSE response, the acquisition job must:

1. Record retrieval timestamp in UTC and Nepal local time, request URL/method, response status, relevant response headers, and exact response bytes.
2. Compute SHA-256 before parsing; preserve the raw payload immutable.
3. Record provider/source name, licence/access scope, schema version, pagination/completeness indicators and any as-of timestamp supplied by the source.
4. Parse without dropping inactive, promoter, mutual-fund, debenture, bond or other instrument rows.
5. Reconcile symbols, IDs, names, active status and instrument type against the full candidate manifest and current snapshot.
6. Produce explicit unmatched, additional, duplicate, inactive, ambiguous and non-equity lists.
7. Require a separate dated primary source or documented official source chain before setting authoritative membership true.
8. Keep lifecycle effective dates unknown unless independently evidenced; do not derive them from first OHLCV rows or current active flags.

## Current gate

- Primary NEPSE universe source captured: **No**.
- Authenticated licensed security-list response captured: **No**.
- Complete raw secondary 652-row catalogue captured: **No**.
- Current candidate set (281) promoted to authoritative membership: **No**.
- Canonical reviewed-row manifest: **unchanged and empty**.
- Production ranking / BUY-list eligibility: **disabled**.

## Next external dependency

Obtain either:
- an authorized ShareHub Data API account with the Security List service enabled and a registered server IP, for a third-party independent current cross-check; or
- a fresh official NEPSE/SEBON/CDSC raw security master with instrument type, active/lifecycle fields and a documented as-of date.

Do not put API credentials in GitHub, source code, issue comments or browser-side frontend code. Keep any acquired secret in an approved server-side secret store. No credentials are requested or assumed in this report.
