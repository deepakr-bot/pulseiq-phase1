import duckdb
con = duckdb.connect("pulseiq.duckdb")
cond = "completed_date < started_date OR (status = 'Done' AND completed_date IS NULL)"
for t in ["raw.fact_task", "clean.fact_task", "dw.fact_task"]:
    try:
        print(t, "rows:", con.sql(f"SELECT COUNT(*) FROM {t}").fetchone()[0],
              "| bad:", con.sql(f"SELECT COUNT(*) FROM {t} WHERE {cond}").fetchone()[0])
    except Exception as e:
        print(t, "ERROR", e)
print(con.sql("SELECT DISTINCT status FROM raw.fact_task").df().to_string())
print(con.sql("SELECT reason, COUNT(*) n FROM main.quarantine WHERE table_name ILIKE '%task%' GROUP BY 1").df().to_string())