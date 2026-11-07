SELECT a.* FROM dw.fact_attendance_monthly a
JOIN dw.dim_employee d ON a.employee_id = d.employee_id
 AND CAST(d.is_current AS VARCHAR) IN ('Y','true','True','1')
WHERE d.exit_date IS NOT NULL
  AND CAST(a.period_end_date AS DATE) > LAST_DAY(CAST(d.exit_date AS DATE))
