import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\n1) Lowest company-wide months")
print(con.sql("""
WITH m AS (SELECT year_month, SUM(present_days)*1.0/SUM(scheduled_days) rate
           FROM dw.v_attendance_monthly GROUP BY 1)
SELECT m.year_month, ROUND(rate*100,1) AS rate_pct,
       ROUND((rate-AVG(rate) OVER())/STDDEV(rate) OVER(),2) AS z, h.holidays
FROM m LEFT JOIN dw.v_holidays_monthly h USING (year_month)
ORDER BY rate LIMIT 5""").df())

print("\n2) Worst department-months")
print(con.sql("""
SELECT department, year_month,
       ROUND(attendance_rate*100,1) AS rate_pct, scheduled_days
FROM dw.v_attendance_monthly ORDER BY attendance_rate LIMIT 6""").df())

print("\n3) Overtime top months")
print(con.sql("""
SELECT year_month, ROUND(SUM(overtime_hours)) AS ot
FROM dw.v_attendance_monthly GROUP BY 1 ORDER BY ot DESC LIMIT 3""").df())

print("\n4) Leave top months by type")
print(con.sql("""
SELECT year_month, leave_type, leave_days
FROM dw.v_leave_monthly ORDER BY leave_days DESC LIMIT 6""").df())