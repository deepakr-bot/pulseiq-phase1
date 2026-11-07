# Orphan and empty-key explanations

- fact_forecast (36 rows): forecast months are Jan to Mar 2027, after the end of dim_date (31 Dec 2026). Future months, expected, not an error.
- fact_ledger (5,688 rows): cost_center_department_id is empty for asset, equity, income and liability lines. Only expense lines belong to a department. By design.
- fact_payroll (2 rows): PI-X0003 (EMP-9001) and PI-X0004 (EMP-9002) have employee_key -1 because their employee ids are not in dim_employee. Planted bad rows, to be caught by the Task 3 quality checks.
- fact_anomaly (31 rows): the scored period (Jun 2025 to Sep 2026) is before the employee's first version in dim_employee, so no employee_key existed on that date. Key left empty, not guessed.
- fact_task (313 rows): the task created date (Mar 2025 to Sep 2026) is before the assignee's first version in dim_employee. Key left empty, not guessed.

# Rule (Think for yourself)
A cost belongs to the department the person was in during the month the cost happened. A person who moved from Sales to Support in July has their June pay in Sales. That is why facts join through employee_key (the version valid at that time), not employee_id.