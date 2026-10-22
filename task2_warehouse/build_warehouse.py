import duckdb

con = duckdb.connect("pulseiq.duckdb")
con.execute("DROP SCHEMA IF EXISTS dw CASCADE")   # safe to re-run
con.execute("CREATE SCHEMA dw")

DIM_PK = {
    "dim_account": ["account_code"], "dim_client": ["client_id"], "dim_date": ["date_key"],
    "dim_department": ["department_id"], "dim_employee": ["employee_key"],
    "dim_leave_type": ["leave_type_code"], "dim_role": ["role_id"],
    "dim_sprint": ["sprint_id"], "dim_team": ["team_id"], "dim_vendor": ["vendor_id"],
}
FACT_PK = {
    "fact_anomaly": ["result_id"], "fact_attrition_risk": ["prediction_id"],
    "fact_forecast": ["forecast_id"], "fact_task": ["task_id"],
    "fact_expense": ["expense_id"], "fact_invoice": ["invoice_id"],
    "fact_invoice_payment": ["payment_id"], "fact_ledger": ["line_id"],
    "fact_headcount_monthly": ["department_id", "date_key"],
    "fact_leave": ["leave_request_id"], "fact_attendance_monthly": ["attendance_fact_id"],
    "fact_payroll": ["payroll_item_id"],
}

def make_table(name, select_sql, pk):
    con.execute(f"CREATE OR REPLACE TEMP TABLE src AS {select_sql}")
    cols = con.execute("DESCRIBE src").fetchall()
    names = [c[0] for c in cols]
    defs = ", ".join(f'"{c[0]}" {c[1]}' for c in cols)
    pk = [p for p in pk if p in names] or [names[0]]    # fallback: first column
    pkdef = ", PRIMARY KEY (" + ", ".join(f'"{p}"' for p in pk) + ")"
    try:
        con.execute(f"CREATE TABLE dw.{name} ({defs}{pkdef})")
        con.execute(f"INSERT INTO dw.{name} SELECT * FROM src")
        return "PK " + ", ".join(pk)
    except Exception as e:
        con.execute(f"DROP TABLE IF EXISTS dw.{name}")
        con.execute(f"CREATE TABLE dw.{name} ({defs})")
        con.execute(f"INSERT INTO dw.{name} SELECT * FROM src")
        return f"NO PK ({pk} not unique or invalid: {str(e)[:70]})"

def emp_key(emp_col, date_expr):
    """employee_key of the version that was valid on that date (one value per row)."""
    return f"""(SELECT MAX(e.employee_key) FROM clean.dim_employee e
                WHERE e.employee_id = f."{emp_col}"
                  AND TRY_CAST(e.valid_from AS DATE) <= {date_expr}
                  AND {date_expr} <= COALESCE(TRY_CAST(e.valid_to AS DATE), DATE '9999-12-31'))"""

tables = [r[0] for r in con.execute(
    "SELECT table_name FROM information_schema.tables WHERE table_schema='clean' ORDER BY 1").fetchall()]

print("=== DIMENSIONS ===")
for t in [t for t in tables if t.startswith("dim_")]:
    print(f"{t:28}", make_table(t, f"SELECT * FROM clean.{t}", DIM_PK.get(t, [])))

print("\n=== FACTS ===")
for t in [t for t in tables if t.startswith("fact_")]:
    if t == "fact_anomaly":
        sql = f"SELECT f.*, {emp_key('employee_id', 'TRY_CAST(f.period AS DATE)')} AS employee_key FROM clean.{t} f"
    elif t == "fact_task":
        d = "COALESCE(TRY_CAST(f.created_date AS DATE), TRY_CAST(f.started_date AS DATE))"
        sql = f"SELECT f.*, {emp_key('assignee_employee_id', d)} AS employee_key FROM clean.{t} f"
    else:
        sql = f"SELECT * FROM clean.{t}"
    print(f"{t:28}", make_table(t, sql, FACT_PK.get(t, [])))

print("\nWarehouse built in schema dw.")