
-- Rows judged bad are listed here (filled by find_bad_rows.py --save). Empty at first.
CREATE TABLE IF NOT EXISTS dw.payroll_excluded (payroll_item_id VARCHAR, reason VARCHAR);

-- All payroll rows except the excluded ones
CREATE OR REPLACE VIEW dw.v_payroll_good AS
SELECT p.*, LAST_DAY(p.period_end_date) AS month_end
FROM dw.fact_payroll p
WHERE p.payroll_item_id NOT IN (SELECT payroll_item_id FROM dw.payroll_excluded);

-- Totals per department and month (no person-level data)
CREATE OR REPLACE VIEW dw.v_payroll_dept_month AS
SELECT g.month_end,
       g.department_id,
       COALESCE(d.department_name, g.department_id) AS department,
       COUNT(DISTINCT g.employee_id) AS employees_paid,
       SUM(g.gross_pay)     AS gross_pay,
       SUM(g.net_pay)       AS net_pay,
       SUM(g.employer_cost) AS employer_cost
FROM dw.v_payroll_good g
LEFT JOIN dw.dim_department d ON g.department_id = d.department_id
GROUP BY 1, 2, 3;

-- Department size, used for the minimum group size rule
CREATE OR REPLACE VIEW dw.v_payroll_dept_size AS
SELECT department_id, department,
       AVG(employees_paid) AS avg_employees,
       MIN(employees_paid) AS min_employees
FROM dw.v_payroll_dept_month
GROUP BY 1, 2;

-- Company totals per month (used for reconciliation only, not shown on the page)
CREATE OR REPLACE VIEW dw.v_payroll_company_month AS
SELECT month_end,
       COUNT(DISTINCT employee_id) AS employees_paid,
       SUM(gross_pay) AS gross_pay, SUM(net_pay) AS net_pay, SUM(employer_cost) AS employer_cost
FROM dw.v_payroll_good
GROUP BY 1;
