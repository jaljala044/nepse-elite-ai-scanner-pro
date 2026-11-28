# Steps 94–95 — lifecycle evidence requests and corporate-action CSV intake

## Step 94: targeted lifecycle evidence request manifest
- Records the two known NEPSE listing-notice URL references and the BENH official-notice request separately.
- Retains the ten unresolved predecessor symbols: BPW, JALPA, KLBSL, MKLB, MMFDB, NLBBL, SABSL, SDLBSL, SAMAJ and SFCL.
- Specifies exact raw bytes, publisher, timestamps, SHA-256, notice metadata and independent review needed for each record.
- Distinguishes listing notice evidence from first executed trade evidence.
- The manifest is a request inventory only. It contains no asserted security-ID mappings or acquired primary documents.

## Step 95: corporate-action CSV intake
- Adds strict CSV schema validation and file-level SHA-256 provenance.
- Enforces publisher/source/tier consistency, timezone-aware timestamps, point-in-time cutoff and duplicate row rejection.
- Preserves source row number and raw file hash for downstream reconciliation.
- Rejects malformed or incomplete exports; never silently repairs source facts.

## Current evidence boundary
No live source was fetched by this implementation. No PDF or CSV was downloaded, and no publisher authenticity is claimed. The request manifest identifies what is needed; operators must supply original files and capture metadata. CSV intake is not action reconciliation, historical dataset admission, factor approval, OHLCV adjustment or production signal activation.
