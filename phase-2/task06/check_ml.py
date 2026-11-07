import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)
print(con.sql("""
SELECT l.leave_request_id, l.start_date, l.end_date, l.days, l.status
FROM dw.fact_leave l
JOIN (SELECT DISTINCT a.employee_id
      FROM dw.fact_attendance_monthly a
      JOIN dw.dim_department dep ON a.department_id = dep.department_id
      WHERE dep.department_name = 'Finance & Accounts') e USING (employee_id)
WHERE l.leave_type_code = 'ML'
ORDER BY l.start_date""").df().to_string())
con.close()