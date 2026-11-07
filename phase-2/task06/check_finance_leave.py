import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)
print(con.sql("""
WITH emp_dept AS (
  SELECT DISTINCT a.employee_id, dep.department_name
  FROM dw.fact_attendance_monthly a
  JOIN dw.dim_department dep ON a.department_id = dep.department_id)
SELECT d.year_month, l.leave_type_code, SUM(l.days) AS days
FROM dw.fact_leave l
JOIN emp_dept e ON l.employee_id = e.employee_id
JOIN dw.dim_date d ON l.start_date_key = d.date_key
WHERE e.department_name = 'Finance & Accounts'
  AND d.year_month BETWEEN '2026-03' AND '2026-09'
  AND UPPER(l.status) NOT IN ('REJECTED','CANCELLED')
GROUP BY 1, 2 ORDER BY 1, 3 DESC""").df().to_string())
con.close()