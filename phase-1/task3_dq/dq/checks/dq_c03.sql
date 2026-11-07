SELECT employee_id, run_id
FROM dw.fact_payroll
GROUP BY 1, 2
HAVING COUNT(*) > 1