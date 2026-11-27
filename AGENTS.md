# Mandatory Agent Work Rules

These rules apply to **every human and AI agent** working anywhere in this repository or on its connected web app, mobile app, backend, data, research, infrastructure, documentation, and web-research tasks. They take priority over an agent's default workflow.

## The non-negotiable rule

**DO NOT REPEAT, RESTART, REPLACE, OVERWRITE, REBASE, FORCE-PUSH, OR OTHERWISE DISTURB WORK THAT IS ALREADY PASSED, APPROVED, MERGED, OR COMPLETED. ONLY START WORK THAT IS VERIFIED AS PENDING OR NOT STARTED.**

For open or running work, inspect the completed portion and its evidence first. Work exclusively on the remaining incomplete acceptance criteria. A task being open does not mean all of its work is unfinished.

## Required check-before-start protocol

Before changing any file, collecting the same evidence again, opening a task, or creating a PR:

1. Read this file and `docs/AGENT_WORK_OWNERSHIP.md`.
2. Inspect the relevant GitHub issue, all linked/dependent issues, open and closed PRs, latest comments/reviews, changed files, commits, exact-head CI, artifacts, and current project progress register.
3. Search the repository and recent history for an existing implementation, evidence capture, report, test, or equivalent task. Check both merged work and open/running work.
4. Classify each acceptance criterion separately as:
   - **COMPLETE / PASSED** — supported by merged code, accepted evidence, or passing checks on the exact relevant commit.
   - **APPROVED** — explicitly approved/reviewed; preserve it unless the owner requests a change.
   - **IN PROGRESS** — already owned or being actively implemented; do not duplicate it. Only its assigned owner may continue its claimed scope.
   - **PENDING** — known remaining work that has not started.
   - **BLOCKED** — cannot proceed because a named dependency, permission, source, decision, or evidence is missing.
   - **NOT STARTED** — no implementation or active owner exists.
   - **FAILED / NEEDS FIX** — concrete failing evidence exists; repair only the failing scope.
5. If the same work is complete, passed, approved, or actively owned, **STOP**. Do not create another issue, branch, PR, implementation, data pull, or evidence run for it. Report the existing authoritative link and status.
6. If only part is complete, preserve it and identify the exact outstanding acceptance criteria. Start only those criteria.
7. If ownership or status is ambiguous, do not edit. First reconcile the issue/PR/register and ask the project owner only if the ambiguity cannot be resolved from repository evidence.

## Ownership and concurrency

- One task/scope has one accountable active owner at a time. Before work starts, claim the specific issue/acceptance criteria and list the intended files or evidence scope in the issue/PR.
- Check for an existing active claim before claiming. If another agent owns it, do not start a competing implementation; coordinate with that owner.
- Parallel work is allowed only when scopes and files are genuinely independent and dependencies are respected. State the boundary explicitly.
- Do not create duplicate issues or PRs for an existing task. Add findings to the canonical issue/PR instead.
- Do not edit files currently being changed by another active PR unless the owner coordinates the change.
- Never overwrite completed evidence, approved artifacts, source snapshots, hashes, reports, or user-finalized values. Corrections require a documented reason, explicit owner authorization where applicable, and a new version with preserved prior lineage.

## Rules for open, running, and stacked work

- Inspect the latest PR head, review state, changed-file list, commit history, CI runs, and dependency chain before touching an open PR.
- Passing CI applies to the exact commit tested; verify the current head. Do not rerun or rebuild a completed/passed task just to claim activity.
- For a running task, continue only its uncompleted acceptance criteria and preserve all passed portions.
- Do not force-push, rewrite history, retarget, close, reopen, merge, or replace another agent's branch/PR. Do not merge any PR unless the project owner explicitly authorizes it.
- Respect dependency order. Do not bypass, duplicate, or independently reimplement a prerequisite already in progress.
- If a fix is required, make the smallest isolated change, add a regression test, and preserve prior commits and evidence.

## Rules for web research and data collection

- Search existing evidence registers, source manifests, artifacts, hashes, reports, and issue comments before collecting anything.
- A prior completed capture is authoritative for its stated scope and retrieval time. Do not recollect the same source/date/range unless a documented gap, expiry, changed source, or reproducible defect justifies it.
- Never overwrite raw source bytes or their metadata. New captures are additive and versioned.
- Do not repeat a completed source investigation merely because another agent is unaware of it. Link the existing evidence.
- Clearly distinguish verified first-party evidence, secondary corroboration, discovery-only results, user-supplied project data, and unresolved claims.
- Never fabricate missing evidence, hashes, dates, permissions, approvals, test results, or source completeness.

## Completion and handoff

A task is complete only when its stated acceptance criteria and required reviews/checks are satisfied. On completion:
1. Update the canonical issue/PR and progress register with exact files, commit SHA, evidence/artifact IDs and hashes where applicable, test/CI run IDs and results, and remaining limitations.
2. Mark only the criteria actually satisfied as complete. Keep blocked and pending criteria visible.
3. Link the authoritative implementation/evidence so later agents can reuse it.
4. Release the ownership claim or identify the next owner and remaining scope.
5. Do not reopen or redo completed work to produce a new report. If new information genuinely invalidates it, open a narrowly scoped follow-up with provenance; preserve the original record.

## Mandatory agent response format

Before acting, state briefly: **existing status; completed/passed scope; active owner (if any); exact pending scope; files/evidence to be touched**.

After acting, state: **what changed; what was deliberately left untouched; exact commit/PR/issue; exact-head checks; remaining pending/blocked scope**.

**Default decision: PRESERVE. If work is not clearly pending or not started, do not touch it.**
