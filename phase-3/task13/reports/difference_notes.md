# Task 13: Difference notes

The combined table is one row per department and month. Each source was aggregated to that grain before joining, and the joins were outer joins so no department-month was dropped.

## Differences found before cleaning

Before excluding non-standard rows, the comparison with the reference showed differences in four measures. All were traced to rows with non-standard IDs.

1. **Employer cost (4 rows, 410,967.46 total).** Four payroll rows have IDs PI-X0001 to PI-X0004 instead of the standard PI-nnnnnn format.
   - PI-X0001 (EMP-0194, Feb 2026, 154,811.89) and PI-X0002 (EMP-0598, May 2025, 61,813.15) repeat an existing employee's cost for the same month, so they are duplicates.
   - PI-X0003 (EMP-9001, Apr 2026, 96,015.00) and PI-X0004 (EMP-9002, Dec 2025, 98,327.42) belong to employee IDs that do not appear in the employee table.
2. **Employees paid (2 rows).** The two unknown employees add one head each in Dec 2025 and Apr 2026.
3. **Late arrivals (2 rows).** Attendance rows FA-X0001 (2 late, Mar 2026, Customer dept D04) and FA-X0003 (3 late, Nov 2025, D01) have non-standard IDs. Their late arrivals explain the gaps.

## Resolution

All eight measures were compared for 198 department-months. After excluding the eight non-standard rows, every measure matches the reference with zero difference.

## Join order

1. Headcount, payroll and attendance were each aggregated to department and month.
2. Headcount was joined to payroll, then the result to attendance (outer joins).
3. Department names were added.
4. Totals were checked before and after the join for employer cost, overtime hours and exits. All three match.