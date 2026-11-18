# Quality and reconciliation report
Run: 2026-11-18 08:54 UTC

| Check | Result | Detail |
|---|---|---|
| ETL freshness: last run within 7 days | FAIL | last finished 2026-10-21 13:40:18.509034, 28 days ago |
| ETL row balance: in = passed + quarantined | PASS | 23 tables checked; mismatches: none |
| Reconcile headcount: metric view = fact table (latest month) | FAIL | view=440, fact=441 |
| Reconcile payroll: cost view = fact table (latest period) | PASS | view=55519621.87000001, fact=55519621.87000001 (a difference may be expected if rows are excluded) |
| Range: attrition between 0 and 100 | PASS | 0 out-of-range rows |
| Logic: on-time tasks never exceed tasks with due dates | PASS | 0 teams break the rule |
| Info: quarantined rows listed for review | PASS | by table: [('fact_task', 20)] |
