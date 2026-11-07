SELECT a.employee_key FROM dw.dim_employee a
JOIN dw.dim_employee b ON a.employee_id = b.employee_id
 AND a.employee_key < b.employee_key AND a.valid_to >= b.valid_from
