# P4.43 acceptance register — 2026-11-27

Status: research safeguards implemented and regression-tested; production acceptance BLOCKED.
PR #161 remains open. Do not merge until trusted-calendar call-site integration and full head CI are verified.

| Requirement | State | Evidence |
|---|---|---|
| Quarantine key reconciliation | PASS 1329/1329 | p443_consolidated_correction_register.csv |
| Raw historical records preserved | No corrective overwrite performed | Separate research output |
| Contract and broker parity | PASS 2401/2401 | p443_broker_parity_timestamp_audit_v1.json |
| Timestamp parsing and order inversions | 2401 parsed, zero inversions | p443_timestamp_chronology_comparison_v1.json |
| Ambiguous price boundaries | BLOCKED 4 fields | p443_tied_execution_boundaries_v1.json |
| Research candidate dataset | PASS 1329 unique keys, 51 candidate fields, 0 admissions | run 46005737106 |
| Scanner/training regressions | PASS | run 46006605805 |
| Broker/performance/walk-forward regressions | PASS | run 46007020655 |
| Deterministic rebuild and hash audit | IMPLEMENTED; execution pending | commit 815bfa70a2ee0bf61040616cdda068e54c6a43e1 |
| Trusted calendar and effective-dated identity | BLOCKED | Primary evidence incomplete |
| Independent source provenance and execution ordering | BLOCKED | Third-party parity does not establish independent origin |
| Historical correction approval | BLOCKED 0/1329 | No authenticated release authority |
| Production acceptance | BLOCKED | No merge, AI recommendations disabled |

Separate independent engineering work from evidence acquisition. Next candidates: issue #106 P4.38 rolling broker profiles, issue #90 P4.33 daily broker ingestion. Work must remain research-only until data gates pass. Do not use synthetic data to claim verified performance.
