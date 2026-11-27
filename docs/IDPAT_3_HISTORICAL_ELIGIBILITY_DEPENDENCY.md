IDPAT-3 CI dependency

This branch inherits `research/issue-20-historical-segment-eligibility` through the IDPAT-2 and IDPAT-1 parent branches. The dependency restores `backend/app/historical_segment_eligibility.py`, required by the repository-wide backend suite. The earlier full-suite error was a missing module in the prior base snapshot, not an IDPAT-3 market-structure test failure. This documentation-only update requests fresh validation after the dependency repair. Existing no-lookahead, session-calendar and NO_TRADE safeguards are unchanged.
