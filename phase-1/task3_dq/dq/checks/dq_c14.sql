SELECT department_id, COUNT(DISTINCT employee_id) AS n
FROM dw.dim_employee GROUP BY 1
HAVING COUNT(DISTINCT employee_id) < 5
