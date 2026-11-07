import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)

print(con.sql("""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_name IN ('fact_attendance_monthly','fact_leave','dim_date')
""").df())

for t in ["fact_attendance_monthly", "fact_leave", "dim_date"]:
    for schema in ["dw", "raw"]:
        try:
            n = con.sql(f"SELECT COUNT(*) FROM {schema}.{t}").fetchone()[0]
            print(f"\n{schema}.{t}: {n} rows")
            print(con.sql(f"DESCRIBE {schema}.{t}").df()[["column_name", "column_type"]])
        except Exception:
            pass