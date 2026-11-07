import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\nTables")
print(con.sql("""SELECT table_schema, table_name, table_type FROM information_schema.tables
    WHERE table_name ILIKE '%task%' OR table_name ILIKE '%team%' OR table_name ILIKE '%sprint%'
       OR table_name IN ('m22_task_completion_rate','m23_on_time_delivery_rate','m24_velocity','m25_average_cycle_time')
    ORDER BY 1, 2""").df().to_string())

for t in ["dw.fact_task", "dw.dim_team", "dw.dim_sprint"]:
    print("\n==", t)
    print(con.sql(f"SELECT COUNT(*) n FROM {t}").df().to_string(index=False))
    print(con.sql(f"DESCRIBE {t}").df()[["column_name", "column_type"]].to_string(index=False))
    print(con.sql(f"SELECT * FROM {t} LIMIT 3").df().to_string())

for c in ["status", "task_status", "priority", "task_type"]:
    try:
        print(f"\nvalues of {c}")
        print(con.sql(f"SELECT {c}, COUNT(*) n FROM dw.fact_task GROUP BY 1 ORDER BY 2 DESC").df().to_string())
    except Exception:
        pass

for v in ["m22_task_completion_rate", "m23_on_time_delivery_rate", "m24_velocity", "m25_average_cycle_time"]:
    print("\n==", v)
    print(con.sql(f"SELECT * FROM main.{v} LIMIT 4").df().to_string())