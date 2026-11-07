CREATE OR REPLACE VIEW dw.v_attendance_monthly AS
SELECT
    d.year_month,
    dep.department_name AS department,
    SUM(a.present_days)    AS present_days,
    SUM(a.scheduled_days)  AS scheduled_days,
    SUM(a.present_days) * 1.0 / NULLIF(SUM(a.scheduled_days), 0) AS attendance_rate,
    SUM(a.late_arrivals)   AS late_arrivals,
    SUM(a.overtime_hours)  AS overtime_hours
FROM dw.fact_attendance_monthly a
JOIN dw.dim_date d         ON a.date_key = d.date_key
JOIN dw.dim_department dep ON a.department_id = dep.department_id
GROUP BY 1, 2;

CREATE OR REPLACE VIEW dw.v_leave_monthly AS
SELECT
    d.year_month,
    l.leave_type_code AS leave_type,
    SUM(l.days)       AS leave_days
FROM dw.fact_leave l
JOIN dw.dim_date d ON l.start_date_key = d.date_key
WHERE UPPER(l.status) NOT IN ('REJECTED', 'CANCELLED')
GROUP BY 1, 2;

CREATE OR REPLACE VIEW dw.v_holidays_monthly AS
SELECT
    year_month,
    SUM(CASE WHEN UPPER(is_holiday) IN ('Y','YES','TRUE','1') THEN 1 ELSE 0 END) AS holidays
FROM dw.dim_date
GROUP BY 1;