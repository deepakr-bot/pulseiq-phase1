import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)
print(con.sql("SELECT is_holiday, COUNT(*) n FROM dw.dim_date GROUP BY 1").df())
print(con.sql("SELECT status, COUNT(*) n FROM dw.fact_leave GROUP BY 1").df())
print(con.sql("DESCRIBE dw.dim_leave_type").df()[["column_name"]])
print(con.sql("SELECT * FROM dw.dim_leave_type LIMIT 10").df())
print(con.sql("SELECT * FROM main.m13_attendance_rate LIMIT 3").df())