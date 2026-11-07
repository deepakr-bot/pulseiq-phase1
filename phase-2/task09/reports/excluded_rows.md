# Excluded payroll rows

4 of 7,344 rows (0.05%) are excluded from the Task 9 page. They are listed in `dw.payroll_excluded` and in `reports/excluded_rows.csv`.

| payroll_item_id | month | department | reason (from the data) |
|---|---|---|---|
| PI-X0002 | 2025-05 | Finance & Accounts | Second payroll row for the same employee in the month; the ID does not follow the normal pattern |
| PI-X0004 | 2025-12 | Operations & IT | Employee is not in the employee master; the ID does not follow the normal pattern |
| PI-X0001 | 2026-02 | Product & Design | Second payroll row for the same employee in the month; the ID does not follow the normal pattern |
| PI-X0003 | 2026-04 | Engineering | Employee is not in the employee master; the ID does not follow the normal pattern |


**Effect:** with these rows excluded, all 18 months match the answer key on gross pay, net pay, employer cost and employees paid. Together they overstated employer cost by about ₹4.11 lakh (0.05%).

I did not add the rows back. For the two duplicates the totals alone cannot show which of the two identical rows is the extra one, so I excluded the one with the unusual ID. Finance should confirm this in the payroll system.

## Message to the finance head (3 calm sentences)

1. While checking payroll against the answer key, I found 4 rows that should not be in the data: two are a second payroll row for the same employee in the same month, and two are for employees who are not in the employee list.
2. I kept these 4 rows out of the dashboard and noted the reason for each, and after that all 18 months match the answer key.
3. Together they made employer cost about 0.05% too high, so I would like to ask you to check in the payroll system whether they need to be corrected.