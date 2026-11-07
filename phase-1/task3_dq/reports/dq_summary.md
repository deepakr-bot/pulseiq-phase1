# Data Quality Report (Task 3)

## Result at a glance
- 14 checks run automatically after every load.
- 2 passed (C02, C09). 12 found bad rows.
- 5 critical checks failed (C01, C03, C04, C12, C14), so the load is stopped.
- All 14 checks were tested with a deliberately bad row. All 14 caught it.
- 9 of 11 planted issues were caught by the checks. The other 2 were already quarantined in Task 1.

## dq_results

| Check | Severity | Bad rows | Status |
|---|---|---|---|
| DQ-C01 | Critical | 5 | FAIL |
| DQ-C02 | Critical | 0 | PASS |
| DQ-C03 | Critical | 2 | FAIL |
| DQ-C04 | Critical | 2 | FAIL |
| DQ-C05 | Warning | 4 | FAIL |
| DQ-C06 | Warning | 39 | FAIL |
| DQ-C07 | Warning | 1 | FAIL |
| DQ-C08 | Warning | 1 | FAIL |
| DQ-C09 | Warning | 0 | PASS |
| DQ-C10 | Warning | 2 | FAIL |
| DQ-C11 | Warning | 5 | FAIL |
| DQ-C12 | Critical | 1 | FAIL |
| DQ-C13 | Critical | 0 | PASS |
| DQ-C14 | Critical | 1 | FAIL |

(Add your screenshot of the run_dq.py output here.)

## What could go wrong (one line per check)
- C01: payroll cost does not match the ledger, so finance numbers are wrong.
- C02: a ledger entry has debits not equal to credits.
- C03: an employee is paid twice in the same run.
- C04: payroll has an employee who is not in the employee table.
- C05: attendance is recorded after the employee left.
- C06: unpaid absence in attendance is not deducted in payroll.
- C07: an invoice is paid more than its total, giving a negative balance.
- C08: an expense total is not amount plus GST.
- C09: a task is completed before it started, or is Done with no completion date.
- C10: a leave request ends before it starts.
- C11: an old AI prediction is shown as current.
- C12: two versions of the same employee overlap in time.
- C13: the pipeline has not loaded in the last 24 hours.
- C14: a group shown to managers is too small and could identify people.

## Critical or warning: my decision
**Critical (stop the load): C01, C02, C03, C04, C12, C13, C14.**
These break totals, joins or privacy for the whole warehouse. Double payroll (C03) and
missing employees (C04) change money totals. Overlapping history (C12) makes facts join
to two versions. A stale pipeline (C13) means managers see old data. Small groups (C14)
are a privacy risk.

**Warning (load, but flag): C05 to C11.**
Each affects a few records and can be fixed later without making the whole warehouse
wrong. The load can continue, but the owner must be told.

## Proof the checks work
Each check was run on a copy of its table with one bad row added. All 14 turned from
fewer bad rows to more bad rows. (Add your screenshot of the test_dq.py output.)

## Planted issues
See reports/dq_missed_issues.md. 9 of 11 were caught. DQ-06 and DQ-07 (20 task rows)
were removed by the Task 1 quarantine before reaching the warehouse, so C09 saw 0.

## Next steps
1. Fix the 5 critical failures first.
2. Add a check that raw rows = warehouse rows + quarantined rows.
3. Review C06 (39 rows) and C14, which were not in the planted list.