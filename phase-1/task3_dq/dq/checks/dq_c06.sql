SELECT a.employee_id, a.period_end_date, a.unpaid_absence_days, p.lop_days
FROM dw.fact_attendance_monthly a
JOIN dw.fact_payroll p ON a.employee_id = p.employee_id
 AND a.period_end_date = p.period_end_date
WHERE ABS(a.unpaid_absence_days - p.lop_days) > 0.5
