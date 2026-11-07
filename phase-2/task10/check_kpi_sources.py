import duckdb
import pandas as pd

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 150)
con = duckdb.connect("pulseiq.duckdb", read_only=True)

VIEWS = ["m04_attrition_rate_monthly", "m11_overtime_share", "m13_attendance_rate", "m22_task_completion_rate"]
print("\nMetric views behind the four KPI targets")
for v in VIEWS:
    print("\n==", v)
    try:
        print(con.sql(f"DESCRIBE main.{v}").df()[["column_name", "column_type"]].to_string(index=False))
        print(con.sql(f"SELECT * FROM main.{v} LIMIT 3").df().to_string())
        print("rows:", con.sql(f"SELECT COUNT(*) FROM main.{v}").fetchone()[0])
    except Exception as e:
        print("  problem:", str(e)[:100])

print("\nHow the four views are defined")
d = con.sql("""SELECT view_name, sql FROM duckdb_views()
               WHERE view_name IN ('m04_attrition_rate_monthly','m11_overtime_share',
                                   'm13_attendance_rate','m22_task_completion_rate') ORDER BY 1""").df()
for _, r in d.iterrows():
    print("\n--", r["view_name"])
    print(r["sql"])

print("\nMetric dictionary rows for these KPIs (definitions only)")
tabs = con.sql("""SELECT table_schema, table_name FROM information_schema.tables
                  WHERE table_name ILIKE '%metric_dictionary%'""").df()
print(tabs.to_string(index=False) if len(tabs) else "  no metric_dictionary table in the database")
for _, t in tabs.iterrows():
    full = f"{t['table_schema']}.{t['table_name']}"
    df = con.sql(f"SELECT * FROM {full}").df()
    print(full, "columns:", list(df.columns))
    mask = df.apply(lambda r: r.astype(str).str.contains(
        "M04|M11|M13|M22|attendance|overtime|attrition|task completion", case=False).any(), axis=1)
    print(df[mask].to_string())

print("\nWhich departments have which targets")
print(con.sql("""SELECT k.department_id AS department_id, d.department_name AS department,
    MAX(k.overtime_share_target_pct) AS overtime_target, MAX(k.task_completion_target_pct) AS task_target,
    COUNT(*) AS n_months FROM dw.kpi_targets k
    LEFT JOIN dw.dim_department d ON d.department_id = k.department_id
    GROUP BY 1, 2 ORDER BY 1""").df().to_string(index=False))
con.close()