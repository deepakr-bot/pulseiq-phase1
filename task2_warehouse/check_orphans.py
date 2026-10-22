import duckdb, pandas as pd

con = duckdb.connect("pulseiq.duckdb")
one = lambda sql: con.execute(sql).fetchone()[0]

CHECKS = [
    ("fact_anomaly", "employee_key", "dim_employee", "employee_key"),
    ("fact_anomaly", "period_key", "dim_date", "date_key"),
    ("fact_attrition_risk", "employee_key", "dim_employee", "employee_key"),
    ("fact_attrition_risk", "department_id", "dim_department", "department_id"),
    ("fact_attrition_risk", "as_of_date_key", "dim_date", "date_key"),
    ("fact_forecast", "department_id", "dim_department", "department_id"),
    ("fact_forecast", "forecast_month_key", "dim_date", "date_key"),
    ("fact_task", "team_id", "dim_team", "team_id"),
    ("fact_task", "sprint_id", "dim_sprint", "sprint_id"),
    ("fact_task", "employee_key", "dim_employee", "employee_key"),
    ("fact_expense", "vendor_id", "dim_vendor", "vendor_id"),
    ("fact_expense", "category_account", "dim_account", "account_code"),
    ("fact_expense", "department_id", "dim_department", "department_id"),
    ("fact_expense", "expense_date_key", "dim_date", "date_key"),
    ("fact_invoice", "client_id", "dim_client", "client_id"),
    ("fact_invoice", "service_line_account", "dim_account", "account_code"),
    ("fact_invoice", "invoice_date_key", "dim_date", "date_key"),
    ("fact_invoice_payment", "invoice_id", "fact_invoice", "invoice_id"),
    ("fact_invoice_payment", "payment_date_key", "dim_date", "date_key"),
    ("fact_ledger", "account_code", "dim_account", "account_code"),
    ("fact_ledger", "cost_center_department_id", "dim_department", "department_id"),
    ("fact_ledger", "date_key", "dim_date", "date_key"),
    ("fact_headcount_monthly", "department_id", "dim_department", "department_id"),
    ("fact_headcount_monthly", "date_key", "dim_date", "date_key"),
    ("fact_leave", "employee_key", "dim_employee", "employee_key"),
    ("fact_leave", "leave_type_code", "dim_leave_type", "leave_type_code"),
    ("fact_leave", "start_date_key", "dim_date", "date_key"),
    ("fact_leave", "end_date_key", "dim_date", "date_key"),
    ("fact_attendance_monthly", "employee_key", "dim_employee", "employee_key"),
    ("fact_attendance_monthly", "date_key", "dim_date", "date_key"),
    ("fact_attendance_monthly", "department_id", "dim_department", "department_id"),
    ("fact_payroll", "employee_key", "dim_employee", "employee_key"),
    ("fact_payroll", "date_key", "dim_date", "date_key"),
    ("fact_payroll", "department_id", "dim_department", "department_id"),
    ("fact_payroll", "role_id", "dim_role", "role_id"),
]

rows = []
for fact, col, dim, dcol in CHECKS:
    total = one(f"SELECT COUNT(*) FROM dw.{fact}")
    nulls = one(f'SELECT COUNT(*) FROM dw.{fact} WHERE "{col}" IS NULL')
    all_roll = one(f"SELECT COUNT(*) FROM dw.{fact} WHERE CAST(\"{col}\" AS VARCHAR) = 'ALL'")
    orphans = one(f"""SELECT COUNT(*) FROM dw.{fact} WHERE "{col}" IS NOT NULL
                      AND CAST("{col}" AS VARCHAR) <> 'ALL'
                      AND CAST("{col}" AS VARCHAR) NOT IN
                          (SELECT CAST("{dcol}" AS VARCHAR) FROM dw.{dim} WHERE "{dcol}" IS NOT NULL)""")
    rows.append((fact, col, dim, total, nulls, all_roll, orphans))

df = pd.DataFrame(rows, columns=["fact", "key_column", "points_to", "rows", "empty_key", "ALL_rollup", "orphans"])
print("=== ORPHAN CHECK ===")
print(df.to_string(index=False))
print("\nTotal orphans:", df["orphans"].sum())
print("Keys needing an explanation (empty or orphan):")
print(df[(df.orphans > 0) | (df.empty_key > 0)].to_string(index=False) or "none")

print("\n=== ROW RECONCILIATION (Task 1 passed vs warehouse) ===")
rec = []
for t, passed in con.execute("SELECT table_name, rows_passed FROM etl_summary ORDER BY 1").fetchall():
    n = one(f"SELECT COUNT(*) FROM dw.{t}")
    rec.append((t, passed, n, "OK" if n == passed else "MISMATCH"))
print(pd.DataFrame(rec, columns=["table", "task1_passed", "warehouse_rows", "result"]).to_string(index=False))