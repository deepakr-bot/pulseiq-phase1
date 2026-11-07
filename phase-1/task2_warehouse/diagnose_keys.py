import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

def diagnose(title, fact, emp_col, date_expr):
    print(f"\n=== {title} ===")
    sql = f"""
    WITH v AS (
        SELECT employee_id,
               MIN(TRY_CAST(valid_from AS DATE)) AS first_from,
               MAX(COALESCE(TRY_CAST(valid_to AS DATE), DATE '9999-12-31')) AS last_to
        FROM dw.dim_employee GROUP BY 1)
    SELECT CASE WHEN v.first_from IS NULL THEN 'employee not in dim_employee'
                WHEN x.d < v.first_from THEN 'date is BEFORE the first version (before hire)'
                WHEN x.d > v.last_to   THEN 'date is AFTER the last version (after exit)'
                ELSE 'date falls in a GAP between versions' END AS reason,
           COUNT(*) AS n, MIN(x.d) AS earliest_date, MAX(x.d) AS latest_date
    FROM (SELECT f.*, {date_expr} AS d FROM dw.{fact} f WHERE f.employee_key IS NULL) x
    LEFT JOIN v ON v.employee_id = x.{emp_col}
    GROUP BY 1 ORDER BY n DESC"""
    print(con.execute(sql).df().to_string(index=False))

diagnose("fact_anomaly: empty keys", "fact_anomaly", "employee_id",
         "TRY_CAST(f.period AS DATE)")
diagnose("fact_task: empty keys", "fact_task", "assignee_employee_id",
         "COALESCE(TRY_CAST(f.created_date AS DATE), TRY_CAST(f.started_date AS DATE))")