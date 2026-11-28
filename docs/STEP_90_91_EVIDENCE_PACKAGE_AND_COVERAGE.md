# Steps 90–91 — raw evidence package and coverage gates

## Step 90: deterministic raw evidence package
- Add file-based intake for operator-supplied raw source artifacts. Verify allowlisted HTTPS publisher domain, publisher ID, primary/secondary tier, retrieved/available timestamps, archive-relative path, non-empty bytes and SHA-256.
- Reject path traversal, duplicate artifact IDs, unsupported domains, future evidence, missing event coverage and hash mismatch.
- Bind identity and action rows to exact raw artifact IDs, hashes, publishers and event coverage. Records cannot cite a different publisher or artifact hash.
- Produce a deterministic manifest digest. The runner does not fetch URLs or treat a URL as proof that bytes were captured.

## Step 91: cross-source coverage and review gate
- Require each requested corporate-action ID to have two distinct publishers including a primary NEPSE/CDSC assertion.
- Run primary notice archive validation, effective-dated identity resolution and corporate-action reconciliation as one fail-closed package.
- Report missing listing/lifecycle notices, unresolved identity symbols, missing action events and incomplete source coverage separately.
- Keep historical dataset admission and price adjustment admission disabled even when evidence is review-ready. Dataset completeness, universe admission, factor-policy approval and replay admission remain separate gates.

## Source coverage
The HTTPS host allowlist accommodates NEPSE/CDSC and project-listed third-party sources: ShareSansar, Chukul, ShareHub Nepal, Punji, Merolagani, NepseAlpha, ChartNepali and Bullhouse. Allowlisting a domain is not publisher authentication or proof of a captured record. Publisher identity and raw evidence still require human review.

## Execution boundary
This PR adds local artifact verification and synthetic tests only. It makes no network requests and does not acquire real records. It does not infer predecessor IDs, admit corporate actions or alter OHLCV. Actual provider exports/PDFs/HTML and capture metadata must be supplied before a real evidence package can pass.
