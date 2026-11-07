SELECT f.employee_id FROM dw.fact_payroll f
LEFT JOIN dw.dim_employee d ON f.employee_id = d.employee_id
WHERE d.employee_id IS NULL
