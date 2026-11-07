CREATE OR REPLACE VIEW dw.v_exits_monthly AS
SELECT
    h.month_start_date AS month,
    COALESCE(dep.department_name, h.department_id) AS department,
    SUM(h.exits) AS exits,
    SUM(h.voluntary_exits) AS voluntary_exits,
    SUM(h.exits) - SUM(h.voluntary_exits) AS other_exits,
    SUM(h.hires) AS hires,
    SUM((h.headcount_start + h.headcount_end) / 2.0) AS avg_headcount
FROM dw.fact_headcount_monthly h
LEFT JOIN dw.dim_department dep ON h.department_id = dep.department_id
GROUP BY 1, 2;

CREATE OR REPLACE VIEW dw.v_exit_tenure AS
SELECT
    COALESCE(dep.department_name, e.department_id) AS department,
    e.exit_date,
    e.employment_status AS exit_type,
    DATEDIFF('day', e.hire_date, e.exit_date) / 365.25 AS tenure_years
FROM dw.dim_employee e
LEFT JOIN dw.dim_department dep ON e.department_id = dep.department_id
WHERE e.is_current = 'Y' AND e.exit_date IS NOT NULL;

CREATE OR REPLACE VIEW dw.v_risk_by_dept AS
WITH latest AS (SELECT MAX(as_of_date) AS d FROM dw.fact_attrition_risk)
SELECT
    r.as_of_date,
    COALESCE(dep.department_name, r.department_id) AS department,
    COUNT(*) AS scored,
    SUM(CASE WHEN UPPER(r.risk_band) = 'HIGH'   THEN 1 ELSE 0 END) AS high,
    SUM(CASE WHEN UPPER(r.risk_band) = 'MEDIUM' THEN 1 ELSE 0 END) AS medium,
    SUM(CASE WHEN UPPER(r.risk_band) = 'LOW'    THEN 1 ELSE 0 END) AS low
FROM dw.fact_attrition_risk r
JOIN latest ON r.as_of_date = latest.d
LEFT JOIN dw.dim_department dep ON r.department_id = dep.department_id
GROUP BY 1, 2;

CREATE OR REPLACE VIEW dw.v_risk_reasons AS
WITH latest AS (SELECT MAX(as_of_date) AS d FROM dw.fact_attrition_risk),
r AS (SELECT * FROM dw.fact_attrition_risk WHERE as_of_date = (SELECT d FROM latest)),
u AS (
    SELECT risk_band, top_reason_1 AS reason FROM r
    UNION ALL SELECT risk_band, top_reason_2 FROM r
    UNION ALL SELECT risk_band, top_reason_3 FROM r
)
SELECT
    risk_band,
    TRIM(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(reason,
        '\s*\([^)]*\)', '', 'g'), '[0-9]+\.?[0-9]*x', '', 'g'), '\s+', ' ', 'g')) AS reason,
    COUNT(*) AS mentions
FROM u
WHERE reason IS NOT NULL
GROUP BY 1, 2;