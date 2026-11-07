CREATE OR REPLACE VIEW v5_department AS
SELECT department_id, department_name FROM dw.dim_department;

CREATE OR REPLACE VIEW v5_company_attrition_12m AS
SELECT month, attrition_12m_pct FROM (
  SELECT month,
         ROUND(100.0 * SUM(exits) OVER w / NULLIF(AVG(hc) OVER w, 0), 2) AS attrition_12m_pct,
         COUNT(*) OVER w AS n_months
  FROM (SELECT month_start_date AS month, SUM(exits) AS exits, SUM(headcount_end) AS hc
        FROM dw.fact_headcount_monthly GROUP BY 1)
  WINDOW w AS (ORDER BY month ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)
) WHERE n_months = 12;

CREATE OR REPLACE VIEW v5_headcount_by_location_tier AS
SELECT l.city_tier, l.tier_number, COUNT(DISTINCT e.employee_id) AS headcount
FROM dw.dim_employee e JOIN dw.dim_location l ON e.work_location = l.work_location
WHERE e.exit_date IS NULL AND CAST(e.is_current AS VARCHAR) IN ('Y','true','True','1')
GROUP BY 1, 2 HAVING COUNT(DISTINCT e.employee_id) >= 5;

CREATE OR REPLACE VIEW v5_headcount_by_work_mode AS
SELECT work_mode, COUNT(DISTINCT employee_id) AS headcount
FROM dw.dim_employee
WHERE exit_date IS NULL AND CAST(is_current AS VARCHAR) IN ('Y','true','True','1')
GROUP BY 1 HAVING COUNT(DISTINCT employee_id) >= 5;