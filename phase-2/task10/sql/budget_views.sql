-- Sign rule: variance = actual - budget. Positive = overspend. Negative = underspend.
-- Variance % = variance / budget * 100

CREATE OR REPLACE VIEW dw.v_budget_month AS
SELECT strftime(CAST(b."month" AS DATE), '%Y-%m') AS month, CAST(b."department_id" AS VARCHAR) AS department_id, SUM(b."budget_payroll_cost") AS budget
FROM dw.budget_payroll_dept_month b 
GROUP BY 1, 2;

CREATE OR REPLACE VIEW dw.v_payroll_actual_month AS
SELECT strftime(month_end, '%Y-%m') AS month, department_id,
       SUM(employer_cost) AS actual, COUNT(DISTINCT employee_id) AS employees_paid
FROM dw.v_payroll_good
GROUP BY 1, 2;

CREATE OR REPLACE VIEW dw.v_payroll_variance AS
SELECT COALESCE(a.month, b.month) AS month,
       COALESCE(a.department_id, b.department_id) AS department_id,
       COALESCE(dep.department_name, COALESCE(a.department_id, b.department_id)) AS department,
       a.employees_paid, b.budget, a.actual,
       a.actual - b.budget AS variance,
       (a.actual - b.budget) * 100.0 / NULLIF(b.budget, 0) AS variance_pct,
       CASE WHEN a.actual > b.budget THEN 'Overspend'
            WHEN a.actual < b.budget THEN 'Underspend' ELSE 'On budget' END AS direction
FROM dw.v_budget_month b
FULL JOIN dw.v_payroll_actual_month a ON a.month = b.month AND a.department_id = b.department_id
LEFT JOIN dw.dim_department dep ON dep.department_id = COALESCE(a.department_id, b.department_id);

CREATE OR REPLACE VIEW main.v10_payroll_variance AS SELECT * FROM dw.v_payroll_variance;
