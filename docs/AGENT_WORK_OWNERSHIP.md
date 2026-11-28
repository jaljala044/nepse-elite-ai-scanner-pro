# Agent Work Ownership and No-Duplicate Protocol

This document operationalizes the mandatory rules in the repository-root `AGENTS.md`. It applies to all agents and collaborators, including agents performing external web research or working on the web/mobile application.

## Status ledger

Use one status per acceptance criterion, not one vague status for an entire issue:

| Status | Meaning | Allowed action |
|---|---|---|
| COMPLETE / PASSED | Evidence and acceptance checks are satisfied | Preserve; do not redo |
| APPROVED | Explicitly accepted by reviewer/owner | Preserve; change only with authorization |
| IN PROGRESS | Active implementation or evidence collection exists | Do not duplicate; coordinate with owner |
| PENDING | Identified, not yet started | Eligible to claim |
| NOT STARTED | No implementation or active owner | Eligible to claim |
| BLOCKED | Dependency/evidence/permission is missing | Do not bypass; document blocker |
| FAILED / NEEDS FIX | A specific test or acceptance criterion fails | Fix only the failing scope |

## Before claiming work

1. Search GitHub issues and PRs by task name, feature, affected files, and acceptance criteria.
2. Inspect merged PRs as well as open/draft PRs. A merged PR may already satisfy the requested work.
3. For open PRs, inspect the latest head SHA, changed files, commits, reviews, CI, and comments. Separate passed criteria from unfinished criteria.
4. Search code, tests, docs, reports, artifacts, and the progress register.
5. Add an ownership note to the canonical issue before editing: agent/owner, acceptance criteria claimed, files or research scope, dependencies, and start time.
6. If an existing owner has claimed overlapping work, stop and coordinate. Do not create a parallel branch or competing PR.

## Safe implementation boundaries

- Prefer one small PR for one genuinely pending scope.
- Do not replace an existing implementation because another approach looks cleaner. Refactoring completed or approved work requires explicit owner approval and a separate rationale.
- Never overwrite raw data, source captures, user-finalized records, audit artifacts, or approved outputs. Append a new version and retain lineage.
- Do not change another PR's branch, target, commits, or review state.
- Do not merge without explicit project-owner authorization.
- Do not interpret a passing old CI run as proof for a different head. Conversely, do not rerun a completed task without a concrete reason.
- If a PR has both passed and pending work, preserve the passed portion and work only on the outstanding criteria.

## Web and external research

Before a new web search/capture, inspect the source register and existing issue notes. Reuse valid prior captures and cite their canonical URLs, timestamps, hashes, and artifacts. Repeat collection only to fill a specific missing date/range/field, validate a documented defect, or refresh evidence whose validity window has expired. Preserve the old capture and explain why the new one is necessary.

## Required task ledger entry

Use this template in the canonical GitHub issue/PR:

```markdown
### Agent ownership and status check
- Checked at (UTC):
- Existing issue/PR/evidence links:
- Existing status: COMPLETE / APPROVED / IN PROGRESS / PENDING / NOT STARTED / BLOCKED / FAILED
- Completed/passed criteria (leave untouched):
- Active owner:
- Exact criteria claimed:
- Files or evidence scope:
- Dependencies:
- Duplicate-work check:
```

## Required completion record

```markdown
### Work completion / handoff
- Changed:
- Preserved / deliberately not touched:
- Commit SHA / PR:
- Exact-head CI and test run IDs:
- Evidence/artifact IDs and hashes:
- Criteria now complete:
- Remaining pending or blocked criteria:
- Ownership released / next owner:
```

## Conflict resolution

When records disagree, do not overwrite either record. Prefer the most authoritative and specific evidence: merged implementation and exact-head CI, approved review, immutable source artifact, then canonical issue/progress register. Record the discrepancy and resolve it with the project owner. User-finalized data remains authoritative for the scope explicitly designated by the user unless the user changes that instruction.


## Canonical ownership record and short-lived lease

The existing GitHub issue is the canonical task/acceptance record; linked PR conversations carry implementation ownership and file-level handoff details. Cross-link this record from the project progress register rather than opening a second task just to claim work.

Post one claim before editing. Include every field below (UTC timestamps):

~~~markdown
### Ownership claim / heartbeat
- Task key / issue:
- Acceptance criteria claimed:
- Actor (stable agent or contributor handle):
- Branch:
- Files or evidence scope:
- Started at (UTC):
- Lease expires at (UTC):
- Last heartbeat at (UTC):
- Dependencies:
- Handoff / release / next owner:
~~~

Use a 30-minute coordination lease by default and renew it with a heartbeat at least every 10 minutes while actively working. Release the claim when stopping or handing off. The claim is stale after its expiry unless renewed in the canonical issue/PR thread.

### Overlap and collision handling

- The first valid, unexpired claim in the canonical thread owns the overlapping acceptance criteria and paths.
- A later claimant must not edit the overlapping files; coordinate with the incumbent and record any agreed split before parallel work.
- If two claims have indistinguishable order, missing timestamps, unclear scope, or uncertain expiry, pause overlapping work and ask the project owner to resolve it.
- Search open PR changed-file lists and recent commits for exact path overlap, not merely similar titles or task keywords.
- A lease does not authorize overwriting another contributor's uncommitted or unreviewed work. Keep changes on separate branches and hand off explicitly.

**Important limitation:** issue comments and Markdown checklists are not a technical mutual-exclusion lock. They do not prevent concurrent writes. This protocol improves visibility and defines when contributors must stop, but it cannot guarantee execution-level locking. That requires an atomic server-side lease/lock service and a mandatory validation at the write or merge boundary. Do not claim that AGENTS.md alone prevents simultaneous file edits.
