import duckdb

checks = {}

checks["dq_c01"] = """
WITH p AS (SELECT strftime(CAST(period_end_date AS DATE), '%Y-%m') AS month, SUM(employer_cost) AS cost
           FROM dw.fact_payroll GROUP BY 1),
l AS (SELECT strftime(CAST(entry_date AS DATE), '%Y-%m') AS month, SUM(debit - credit) AS exp
      FROM dw.fact_ledger
      WHERE CAST(account_code AS VARCHAR) IN ('5001','5002','5003','5004','5005') GROUP BY 1)
SELECT p.month, p.cost, l.exp, p.cost - l.exp AS diff
FROM p JOIN l USING (month) WHERE ABS(p.cost - l.exp) > 0.01
"""

checks["dq_c02"] = """
SELECT entry_id FROM dw.fact_ledger GROUP BY entry_id
HAVING ABS(SUM(debit) - SUM(credit)) > 0.005
"""

checks["dq_c04"] = """
SELECT f.employee_id FROM dw.fact_payroll f
LEFT JOIN dw.dim_employee d ON f.employee_id = d.employee_id
WHERE d.employee_id IS NULL
"""

checks["dq_c05"] = """
SELECT a.* FROM dw.fact_attendance_monthly a
JOIN dw.dim_employee d ON a.employee_id = d.employee_id
 AND CAST(d.is_current AS VARCHAR) IN ('Y','true','True','1')
WHERE d.exit_date IS NOT NULL
  AND CAST(a.period_end_date AS DATE) > LAST_DAY(CAST(d.exit_date AS DATE))
"""

checks["dq_c06"] = """
SELECT a.employee_id, a.period_end_date, a.unpaid_absence_days, p.lop_days
FROM dw.fact_attendance_monthly a
JOIN dw.fact_payroll p ON a.employee_id = p.employee_id
 AND a.period_end_date = p.period_end_date
WHERE ABS(a.unpaid_absence_days - p.lop_days) > 0.5
"""

checks["dq_c07"] = """
SELECT invoice_id FROM dw.fact_invoice
WHERE amount_paid > total_amount + 0.01 OR balance_due < -0.01
"""

checks["dq_c08"] = """
SELECT expense_id FROM dw.fact_expense
WHERE ABS(total_amount - (amount_excl_gst + gst_amount)) > 0.01
"""

checks["dq_c09"] = """
SELECT task_id FROM dw.fact_task
WHERE completed_date < started_date
   OR (status = 'Done' AND completed_date IS NULL)
"""

checks["dq_c10"] = """
SELECT leave_request_id FROM dw.fact_leave WHERE end_date < start_date
"""

checks["dq_c11"] = """
SELECT prediction_id FROM dw.fact_attrition_risk
WHERE as_of_date < (SELECT MAX(as_of_date) FROM dw.fact_attrition_risk) - 7
"""

checks["dq_c12"] = """
SELECT a.employee_key FROM dw.dim_employee a
JOIN dw.dim_employee b ON a.employee_id = b.employee_id
 AND a.employee_key < b.employee_key AND a.valid_to >= b.valid_from
"""

checks["dq_c13"] = """
SELECT MAX(finished_at) AS last_load FROM main.etl_run_log
HAVING MAX(finished_at) IS NULL
    OR MAX(finished_at) < CAST(now() AS TIMESTAMP) - INTERVAL 24 HOUR
"""

# change 5 to the min_group_size in your metric dictionary
checks["dq_c14"] = """
SELECT department_id, COUNT(DISTINCT employee_id) AS n
FROM dw.dim_employee GROUP BY 1
HAVING COUNT(DISTINCT employee_id) < 5
"""

for name, sql in checks.items():
    open(f"dq/checks/{name}.sql", "w").write(sql.strip() + "\n")

con = duckdb.connect("pulseiq.duckdb")
con.sql("CREATE TABLE IF NOT EXISTS main.etl_run_log(finished_at TIMESTAMP)")
con.sql("INSERT INTO main.etl_run_log VALUES (CAST(now() AS TIMESTAMP))")
con.close()
print("13 check files created")