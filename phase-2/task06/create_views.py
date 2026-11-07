import duckdb
con = duckdb.connect("pulseiq.duckdb")
con.execute(open("sql/attendance_views.sql").read())
for v in ["v_attendance_monthly", "v_leave_monthly", "v_holidays_monthly"]:
    print(v)
    print(con.sql(f"SELECT * FROM dw.{v} LIMIT 5").df())
con.close()