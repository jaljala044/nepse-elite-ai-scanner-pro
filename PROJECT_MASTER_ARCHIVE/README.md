# NEPSE AI Project Master Archive

**Archive status:** Initial archive structure created; evidence inventory is based on repository records inspected on 2026-11-26.  
**Project repository:** [jaljala044/nepse-elite-ai-scanner-pro](https://github.com/jaljala044/nepse-elite-ai-scanner-pro)  
**Archive branch:** `docs/project-master-archive`  
**Project owner target:** 281 equities + 47 mutual funds; 120 trading days for v1, with longer history as a later objective.

## Purpose

This is the central index for project datasets, reports, source links, code/workflow evidence, user-supplied evidence attachments, and completion state. It is an index and governance record; it does not imply that every referenced file has been copied into this repository.

## Archive contents

| File | Purpose |
|---|---|
| [DATASET_REGISTER.csv](DATASET_REGISTER.csv) | Dataset/archive inventory, coverage, revision, evidence and limitations |
| [EVIDENCE_REGISTER.csv](EVIDENCE_REGISTER.csv) | Reports, CI runs, artifacts, attachment evidence and local-only outputs |
| [SOURCE_LINKS.csv](SOURCE_LINKS.csv) | Primary, secondary and community source links with use restrictions |
| [COMPLETION_STATUS.csv](COMPLETION_STATUS.csv) | Workstream status, acceptance criteria, blockers and next actions |

## Evidence status vocabulary

- `VERIFIED_IN_REPO`: file/path or report was inspected in the GitHub repository.
- `VERIFIED_RUN`: successful workflow run is recorded; this verifies the tested workflow path, not all underlying real-world data.
- `ATTACHMENT_IN_CHAT`: user-provided file is known to exist in the project conversation, but was not confirmed in this repository.
- `LOCAL_ONLY_NOT_COMMITTED`: output was generated locally and its presence in GitHub is explicitly not established.
- `REFERENCED_NOT_REINSPECTED`: referenced by an inspected report but not individually opened during this archive build.
- `UNVERIFIED`: source or claim needs additional evidence.

Completion states: `COMPLETE`, `PARTIAL`, `BLOCKED`, `NOT_STARTED`, `UNKNOWN`. A green CI run is not equivalent to real-data acceptance.

## Important project decisions and guardrails

1. No historical OHLCV or floorsheet archive is currently approved as canonical/training data.
2. The active instrument register target of 281 equities + 47 mutual funds remains unverified against a dated primary exchange register.
3. The official date-level NEPSE trading/session calendar has not been populated; the canonical calendar is reported to contain zero verified rows.
4. Historical OHLCV exceptions (1,331 invalid rows plus 8 cross-source conflicts) remain quarantined.
5. Floorsheet source matching is not proof of independent provenance. Keep publishers/revisions separate.
6. Broker codes are not beneficial-owner identities; current directory matches are not automatically historical legal-entity verification.
7. Source licences for code do not automatically grant rights to upstream market data. Review data-use terms before storage, training, or redistribution.
8. Do not invent missing values, session dates, instrument membership, broker identities, or successful live runs.

## Key inspected project records

- [Master progress register](../docs/NEPSE_AI_MASTER_PROGRESS_REGISTER_2026-11-25.md)
- [P1 acceptance status and next five tasks](../docs/P1_ACCEPTANCE_STATUS_AND_NEXT_5_2026-11-25.md)
- [Data sources](../docs/DATA_SOURCES.md)
- [Roadmap](../docs/ROADMAP.md)
- [Cross-repository OHLCV audit](../docs/CROSS_REPOSITORY_OHLCV_AUDIT_2026-11-25.md)
- [Historical OHLCV audit](../docs/HISTORICAL_OHLCV_AUDIT_2026-11-24.md)
- [Floorsheet provenance review](../docs/FLOORSHEET_SOURCE_PROVENANCE_REVIEW_2026-11-25.md)
- [Pipeline readiness](../docs/NEPSE_DATA_PIPELINE_READINESS_2026-11-25.md)
- [P1 evidence manifest contracts](../docs/P1_EVIDENCE_MANIFEST_CONTRACTS_2026-11-25.md)

## Known evidence not yet physically consolidated here

- `NEPSE_Floorsheet_Evidence.xlsx` and `NEPSE_Chart_Evidence.pdf` were supplied as attachments in the project conversation. They have not been verified as repository files; add them only after obtaining the original files and recording SHA-256, byte size, capture date, symbol/date scope and source URL.
- `ohlcv_exception_ledger_2026-11-25.csv` (~1.09 MB) and `ohlcv_exception_ledger_2026-11-25.json` (~1.98 MB) were reported as local outputs, not committed data. The validator code/tests are in the repository, but do not treat these ledger payloads as archived here.
- GitHub Actions artifacts are referenced by run/artifact IDs in the evidence register. Workflow artifacts may expire; preserve important outputs in a durable, rights-cleared location and record their hashes.

## How to update

After every material work session:
1. Add each new source file or report to the appropriate CSV register.
2. Record immutable source revision/path, SHA-256 (where bytes are available), byte count, retrieval time and rights status.
3. Link the exact GitHub commit/workflow run/artifact.
4. Update completion status only when acceptance criteria and evidence are satisfied.
5. Keep unresolved findings visible; never overwrite source records or silently resolve conflicts.
6. Review this archive alongside the master progress register so the two remain consistent.

**Initial inventory date:** 2026-11-26.  
**Note:** this archive is a curated inventory, not a claim that all historical data has been downloaded or verified.
