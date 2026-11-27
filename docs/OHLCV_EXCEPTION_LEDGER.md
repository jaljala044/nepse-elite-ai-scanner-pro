# OHLCV row-level exception ledger

## Pinned audit inputs

This ledger is reproducibly generated from the read-only audit artifact for workflow run
[45397942163](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45397942163),
artifact ID `14921283424`.

- Artifact ZIP SHA-256: `e1e5e8ac84e1d2ad273b605725c69614693a831117f96a6b8d7f5af2b4c81cb8`
- `nepse-smc-data` commit: `937cfcf93d78dfcf28a9f09bb13291447988157b`
- `nepse-history-starter` commit: `b60728d39f34e0f9e428675d817fd52ed2784da6`
- SocrateAI cross-check commit: `f602a5b61e68582d28834d16f71151a4bae98d5b`

## Rebuild

Download the original workflow artifact ZIP and run:

```bash
python scripts/build_ohlcv_exception_ledger.py \
  --artifact-zip ohlcv-exception-ledger.zip \
  --artifact-id 14921283424 \
  --artifact-sha256 e1e5e8ac84e1d2ad273b605725c69614693a831117f96a6b8d7f5af2b4c81cb8 \
  --output-dir data/audits/ohlcv-exception-ledger
```

The builder verifies the ZIP hash before reading it and fails closed if the exception
counts differ from the pinned baseline. It emits JSON and CSV with the same unique
exception IDs. The full ledger is a generated output; the immutable source artifact
remains the underlying evidence.

## Ledger baseline

| Exception class | Count | Disposition |
| --- | ---: | --- |
| Invalid OHLC rows | 1,331 | `quarantined_unresolved` |
| Cross-source conflicts with user-authoritative evidence | 5 | `resolved_with_user_authoritative_evidence` |
| Other cross-source conflicts | 3 | `quarantined_unresolved` |
| **Total unique exceptions** | **1,339** | **No canonical promotion** |

Every invalid row retains the pinned source commit, ticker path, file SHA-256,
original CSV line, raw row and violated validation rule. Every cross-source conflict
retains both source values, both pinned commits, paths and file hashes. The original
CSV line number for conflict rows was not present in the source audit artifact and
is deliberately kept null rather than inferred.

SocrateAI classifications, daily-file hashes and comparisons are attached where
available as corroboration only. SocrateAI is not an exchange-origin truth source.
No source wins automatically, and no raw CSV is modified, repaired, merged or
promoted.

## User-authoritative 2025-07-28 conflict resolutions

The user explicitly designated their supplied OHLC chart readings and floorsheet
quantity/turnover for BGWT, MEHL, RAWA, RHGCL and ULHC on 2025-07-28 as final and
authoritative. These five conflict records therefore use
`resolved_with_user_authoritative_evidence`, not unresolved quarantine. Both original
pinned-source rows remain intact in `source_evidence`; the resolved values are kept
separately in `resolution_evidence.authoritative_values`.

The authoritative rows (OHLC, shares, turnover NPR, trades) are:

| Symbol | Open | High | Low | Close | Shares | Turnover (NPR) | Trades |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BGWT | 940.00 | 992.00 | 933.40 | 957.17 | 14,028 | 13,256,345.00 | 194 |
| MEHL | 471.10 | 480.50 | 460.00 | 475.63 | 29,753 | 14,008,898.10 | 333 |
| RAWA | 796.00 | 811.00 | 780.30 | 796.90 | 3,165 | 2,515,662.50 | 74 |
| RHGCL | 346.70 | 362.00 | 341.40 | 357.05 | 296,715 | 103,872,614.40 | 1,030 |
| ULHC | 509.00 | 515.00 | 495.00 | 510.75 | 32,288 | 16,273,342.10 | 300 |

Evidence is the user-provided `NEPSE_Chart_Evidence.pdf`, page 1, which records
ShareHub daily OHLC and reconciled ShareHub floorsheet totals. The user authority
instruction controls the disposition for these exact five records. No other conflict
is resolved by extrapolation. In particular, the 2026-11-19 API, HRL and RHGCL
conflicts remain quarantined unresolved.

This row-level disposition is not blanket authorization to promote either source
archive or to ingest the five rows automatically. The generated ledger records
`canonical_promotion_allowed: false` and `raw_source_rows_modified: false` for
each user-authoritatively resolved record. The supplied PDF binary's SHA-256 was not
captured in this run; the filename and page are retained as the evidence locator
rather than inventing a checksum.

## Retained generated output

The pull-request workflow rebuilds the ledger from the pinned source artifact, verifies the archive SHA-256, checks the 1,339 unique JSON/CSV IDs, the exact five user-authoritative resolutions, and the remaining unresolved dispositions, and uploads the generated JSON/CSV package as a 90-day GitHub Actions artifact. The first retained artifact is [run 45929360486, artifact 15167354458](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45929360486). Its downloaded outer ZIP SHA-256 is `125f786aadff0dda295f153f51caa097d383fd1331138b2126c668f3d8e2d8e9`; the inner generated ZIP SHA-256 is `6e8a3ee7f202af6386bc39a1b72c100ea6af27ef3978d40a6a05836e43e4d66c`.

## Validation

`scripts/validate_ohlcv_exception_ledger.py` validates the generated JSON/CSV pair.
`tests/test_ohlcv_exception_ledger.py` covers count, identity and unresolved-disposition
controls; `tests/test_ohlcv_exception_ledger_builder.py` covers deterministic building,
two-sided conflict provenance and fail-closed count drift.
