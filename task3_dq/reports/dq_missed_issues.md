## Why I missed DQ-06 and DQ-07
My C09 check passed on dw.fact_task, so it did not flag these. The diagnosis shows
raw.fact_task contains all 20 bad rows (12 for DQ-06, 8 for DQ-07), but clean and dw
have 0. The Task 1 ETL data contracts quarantined exactly those 20 rows (28,868 raw
rows - 20 quarantined = 28,848 in dw). So the problems were stopped upstream.

This is not a failure of C09. Its logic was proven by a bad-row test (0 -> 1 bad rows).
It is a blind spot: a check on the warehouse cannot see rows that never reach it.

## What I would add
- A reconciliation check: raw rows = warehouse rows + quarantined rows, per table.
  Any gap means rows were lost silently.
- Report the quarantine count in the DQ summary, so a manager sees what was removed.