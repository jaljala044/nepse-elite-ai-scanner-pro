# Project-wide integration checkpoint — 2026-11-27

Snapshot: 88 open PRs and 10 non-PR open issues in the scanner repository; main tree 1,899 files. This is a repository inventory and targeted evidence review, not full source-code acceptance. No merge, closure or data promotion performed.

## Canonical ownership and dependencies
- Main already contains index intelligence, verified sector rotation, broker memory and dashboard, early candidate detection, and evidence-gated Part 2 snapshot (see main docs/PART2_INTELLIGENCE_INTEGRATION_REGISTER_2026-11-27.md). Do not port competing implementations indiscriminately.
- Historical replay stack PRs #213 -> #214 -> #215 -> #218 -> #227 -> #228 -> #229 -> #230: review interfaces against PR #150 before selecting a canonical implementation. #230 head 1d4c09ace545ae7f1d95c29e3c61f3a7e47cb861 has both PR workflows passed. This is not a merge authorization.
- Portfolio privacy #203 and private ledger #194 -> holding preferences #219: do not expose caller-attested research endpoints as authenticated personal-account features.
- #202 main historical segment dependency fix: no PR workflow runs returned for head 2b89963d8422234b3b6ac737a314b62c278104da; status unverified, not failed.
- #150 head 8d2173dba073662c65ecb2780cde8d92c6b695d3: both workflows passed; mergeable against its stacked base #145, not necessarily main.
- Existing data work #4, #5, #6, #20, #90, #106, #134, #146 remains open. Preserve raw evidence and UNKNOWN semantics. Main P1 acceptance checkpoint is blocked for production backtesting.

## Next ten acceptance gates, ordered by dependency
1. Verify #202 dependency and main CI; do not merge without approval.
2. Review overlapping PR families and designate canonical interfaces; no automatic closure.
3. Complete official calendar, OHLCV, corporate-action and universe eligibility; reconcile quarantine.
4. Validate official index/sector sources and complete broker captures (#90/#106/#134/#146).
5. Reconcile six-scanner replay contracts with #150 and #230, freeze methodology and signal identity.
6. Validate T+2, circuit bands, costs, portfolio cash, and outcomes on identical point-in-time cohorts; publish coverage and uncertainty.
7. Integrate private portfolio storage/preferences and authentication before personal account endpoints.
8. Connect main frontend to trusted backend contracts; test loading, unknown, invalid and successful states.
9. Confirm mobile repository or implement a client after shared API and privacy acceptance; no dedicated mobile tree observed on main.
10. Run independent holdout and end-to-end release acceptance; no accuracy ranking or production BUY until data and execution gates pass.

## Release status
Research only. No verified performance, full historical coverage, mobile build, or production authorization established. CI passing is not trading accuracy. Preserve existing independent scanner outputs, 25/25/15/10/10/5/5/5 master weighting and all four horizons. No Tinyfish use.
