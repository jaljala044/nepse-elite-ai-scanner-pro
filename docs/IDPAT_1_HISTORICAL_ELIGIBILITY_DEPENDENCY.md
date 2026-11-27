IDPAT-1 CI dependency

This branch is based on `research/issue-20-historical-segment-eligibility`, which provides the historical-segment evaluator imported by the repository-wide backend test suite. The prior full-suite error was a missing module in the base snapshot, not a failure in the IDPAT-1 engine tests. This documentation-only commit requests fresh validation against the dependency-complete base. No engine behavior or data evidence has changed.
