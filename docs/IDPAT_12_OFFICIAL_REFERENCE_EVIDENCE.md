# IDPAT-12 — Official reference-data evidence admission

## Delivered
- Reuses the existing calendar evidence manifest and official universe snapshot validators.
- Re-hashes every raw evidence file from a confined evidence root; rejects missing files, symlinks, path traversal and hash mismatch.
- Requires approved rights, independently validated source, finality, UTC retrieval before decision cutoff and reviewer-approved source independence groups.
- Checks every explicitly expected calendar date has exactly one all-securities claim with the configured number of independent source groups; missing dates are not inferred from weekdays or filled.
- Verifies the universe snapshot source ID, URL, raw hash and retrieval timestamp match its captured artifact; validates exact configurable equity and mutual-fund counts and dated instrument identity.
- Output permits research review only. Production promotion is unconditionally false.

## Evidence boundary
- URLs are constrained to official NEPSE/SEBON HTTPS hosts but that alone does not prove that a publisher's bytes are authentic; the raw payload is re-hashed and provenance still requires trusted capture and review.
- Fixtures are synthetic. No real official NEPSE calendar or universe is included or asserted.
