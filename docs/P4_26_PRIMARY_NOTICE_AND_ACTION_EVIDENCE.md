# P4.26 — Primary notice archive and corporate-action evidence

## Step 86 — primary lifecycle document archive
- Validate operator-supplied raw PDF files against a manifest: exact official HTTPS host, HTTP 200, PDF content type and signature, retrieval/availability timestamps, publisher ID, archive-relative path and SHA-256.
- Required event IDs must each have one verified document. Missing documents, path traversal, duplicate entries, hash mismatch, future evidence and non-primary domains block.
- Link predecessor-to-successor identity records only to verified archived primary documents and require independent reviewer approval.
- Current target gaps remain: two NEPSE listing-notice PDFs and the BENH listing notice; ten predecessor symbols (BPW, JALPA, KLBSL, MKLB, MMFDB, NLBBL, SABSL, SDLBSL, SAMAJ, SFCL) remain unresolved until dated stable-ID evidence is supplied.
- A listing notice can establish listing/release facts stated in the notice; it does not automatically establish first executed trade or a historical stable-ID interval.

## Step 87 — typed corporate-action evidence ledger
- Record action ID, symbol/security ID, type, announcement and availability timestamps, ex-date, source/publisher, source tier, raw evidence hash, status, adjustment factor/methodology and independent review.
- Require two distinct publishers including NEPSE/CDSC primary evidence. Conflicting symbol/ID/type/ex-date/status/factor/methodology assertions block the event.
- Bonus, rights, split and reverse-split factors require an explicit methodology identifier; the validator does not calculate or invent factors.
- Review-ready records still do not authorize price adjustment. Temporal identity, action-universe completeness and the separately approved adjustment policy remain mandatory.

## Current execution outcome
The implementation is an intake/validation gate for supplied raw files and records. The repository currently contains two official NEPSE PDF URL references and a third-party BENH listing article, but no verified archived PDF bytes for those three notices in this task. The ShareHub provider lead remains unauthenticated/not acquired. Therefore no predecessor IDs are assigned, no corporate-action events are admitted, and no OHLCV is adjusted. Tests use synthetic PDF bytes only.
