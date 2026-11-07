import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)
for t in ["raw.fact_task", "clean.fact_task", "dw.fact_task"]:
    try:
        print(t, con.sql(f"SELECT COUNT(*) FROM {t}").fetchone()[0],
              "distinct task_id:", con.sql(f"SELECT COUNT(DISTINCT task_id) FROM {t}").fetchone()[0])
    except Exception as e:
        print(t, "not found")
print(con.sql("""SELECT table_schema, table_name FROM information_schema.tables
                 WHERE table_name ILIKE '%quarantine%' OR table_name ILIKE '%reject%'
                    OR table_name ILIKE '%dq_%'""").df())