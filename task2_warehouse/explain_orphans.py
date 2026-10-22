import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

def show(title, sql):
    print(f"\n=== {title} ===")
    print(con.execute(sql).df().to_string(index=False))

show("1. fact_anomaly: empty employee_key", """
    SELECT CASE WHEN EXISTS (SELECT 1 FROM dw.dim_employee e WHERE e.employee_id = f.employee_id)
                THEN 'employee exists, but no version valid on that date'
                ELSE 'employee_id not in dim_employee' END AS reason,
           COUNT(*) AS n
    FROM dw.fact_anomaly f WHERE f.employee_key IS NULL GROUP BY 1""")

show("2. fact_forecast: orphan month keys", """
    SELECT (SELECT MIN(date) FROM dw.dim_date) AS dim_date_from,
           (SELECT MAX(date) FROM dw.dim_date) AS dim_date_to,
           MIN(forecast_month) AS orphan_months_from,
           MAX(forecast_month) AS orphan_months_to,
           COUNT(*) AS n
    FROM dw.fact_forecast
    WHERE CAST(forecast_month_key AS VARCHAR) NOT IN (SELECT CAST(date_key AS VARCHAR) FROM dw.dim_date)""")

show("3. fact_task: empty employee_key", """
    SELECT CASE WHEN assignee_employee_id IS NULL THEN 'task has no assignee'
                ELSE 'assigned, but no version valid on created date' END AS reason,
           status, COUNT(*) AS n
    FROM dw.fact_task WHERE employee_key IS NULL GROUP BY 1, 2 ORDER BY n DESC""")

show("4. fact_ledger: empty cost center by account type", """
    SELECT a.account_type,
           CASE WHEN l.cost_center_department_id IS NULL THEN 'no cost center' ELSE 'has cost center' END AS cost_center,
           COUNT(*) AS n
    FROM dw.fact_ledger l LEFT JOIN dw.dim_account a ON a.account_code = l.account_code
    GROUP BY 1, 2 ORDER BY 1, 2""")

show("5. fact_payroll: orphan employee_key", """
    SELECT payroll_item_id, employee_id, employee_key, run_id, date_key
    FROM dw.fact_payroll
    WHERE CAST(employee_key AS VARCHAR) NOT IN (SELECT CAST(employee_key AS VARCHAR) FROM dw.dim_employee)""")