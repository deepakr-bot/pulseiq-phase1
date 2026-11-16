# Task 16: New-department test notes

## Test
- One row added to `fact_ledger` in a test copy of the database
- Department: D99
- Account: 4001 (Product Sales)
- Amount: 1,000,000 credit
- Month: September 2026
- The real database was not changed.

## Result
- September 2026 revenue (`m16_revenue`) was 80,268,200 in both the original and the test copy.
- The report ran without errors, but it did not include the new row.
- The report has no department breakdown, so D99 is not named anywhere.

## Cause
`m16_revenue` is a stored table built earlier, not recalculated from `fact_ledger`. Adding a ledger row does not update it.

## What would break
- Any KPI built from a metric table is missing a new department until that table is rebuilt.
- The report shows no warning, so the missing amount is invisible.
- Department-level views would miss a department the metric tables don't cover.

## Fix
- Rebuild the metric tables after each new department is posted.
- Add a check that the ledger total for each month matches the metric total.