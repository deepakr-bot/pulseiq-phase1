import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\nFinance absence breakdown")
print(con.sql("""
SELECT d.year_month,
       SUM(a.scheduled_days)      AS scheduled,
       SUM(a.present_days)        AS present,
       SUM(a.wfh_days)            AS wfh,
       SUM(a.paid_leave_days)     AS paid_leave,
       SUM(a.unpaid_absence_days) AS unpaid_abs,
       SUM(a.half_days_unpaid)    AS half_unpaid
FROM dw.fact_attendance_monthly a
JOIN dw.dim_date d ON a.date_key = d.date_key
JOIN dw.dim_department dep ON a.department_id = dep.department_id
WHERE dep.department_name = 'Finance & Accounts'
GROUP BY 1 ORDER BY 1""").df().to_string())

print("\nLate arrivals per 100 scheduled days (company)")
print(con.sql("""
SELECT year_month, ROUND(SUM(late_arrivals)*100.0/SUM(scheduled_days),1) AS late_per_100
FROM dw.v_attendance_monthly GROUP BY 1 ORDER BY 1""").df().to_string())