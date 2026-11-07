import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)
for t in ["fact_attendance_monthly", "fact_leave", "dim_date", "dim_department"]:
    print("\n==", t)
    try:
        print(con.sql(f"DESCRIBE dw.{t}").df()[["column_name", "column_type"]].to_string(index=False))
    except Exception as e:
        print("not found:", str(e)[:80])