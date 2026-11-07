import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\nCompany month summary")
print(con.sql("""
WITH a AS (
  SELECT year_month, SUM(present_days)*100.0/SUM(scheduled_days) AS rate_pct,
         SUM(late_arrivals) AS late, SUM(overtime_hours) AS ot
  FROM dw.v_attendance_monthly GROUP BY 1),
l AS (SELECT year_month, SUM(leave_days) AS leave_days
      FROM dw.v_leave_monthly GROUP BY 1)
SELECT a.year_month, ROUND(a.rate_pct,1) AS rate_pct, a.late,
       ROUND(a.ot) AS ot, h.holidays, l.leave_days
FROM a LEFT JOIN l ON a.year_month = l.year_month
       LEFT JOIN dw.v_holidays_monthly h ON a.year_month = h.year_month
ORDER BY 1""").df().to_string())

print("\nFinance & Accounts by month")
print(con.sql("""
SELECT year_month, ROUND(attendance_rate*100,1) AS rate_pct, scheduled_days,
       late_arrivals, ROUND(overtime_hours) AS ot
FROM dw.v_attendance_monthly
WHERE department = 'Finance & Accounts' ORDER BY 1""").df().to_string())

print("\nExecutive Office size")
print(con.sql("""
SELECT year_month, scheduled_days, present_days
FROM dw.v_attendance_monthly
WHERE department = 'Executive Office' ORDER BY 1""").df().to_string())

print("\nHoliday dates in Jan and May 2026")
print(con.sql("""
SELECT date, day_of_week FROM dw.dim_date
WHERE year_month IN ('2026-01','2026-05')
  AND UPPER(is_holiday) IN ('Y','YES','TRUE','1') ORDER BY date""").df())