import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)
print(con.sql("""
WITH m AS (
  SELECT year_month, SUM(present_days)*1.0/SUM(scheduled_days) AS rate
  FROM dw.v_attendance_monthly GROUP BY 1)
SELECT m.year_month, ROUND(rate,4) AS rate,
       ROUND((rate - AVG(rate) OVER ()) / STDDEV(rate) OVER (), 2) AS z_score,
       h.holidays
FROM m LEFT JOIN dw.v_holidays_monthly h USING (year_month)
ORDER BY ABS(z_score) DESC LIMIT 6
""").df())