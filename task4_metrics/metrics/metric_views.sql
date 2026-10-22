CREATE OR REPLACE VIEW m01_headcount AS
SELECT department_id, month_start_date AS month, headcount_end AS headcount
FROM dw.fact_headcount_monthly WHERE headcount_end >= 5;

CREATE OR REPLACE VIEW m02_hires AS
SELECT department_id, month_start_date AS month, hires
FROM dw.fact_headcount_monthly WHERE headcount_end >= 5;

CREATE OR REPLACE VIEW m03_exits AS
SELECT department_id, month_start_date AS month, exits
FROM dw.fact_headcount_monthly WHERE headcount_end >= 5;

CREATE OR REPLACE VIEW m04_attrition_rate_monthly AS
SELECT department_id, month_start_date AS month,
       ROUND(100.0 * exits / NULLIF(headcount_start, 0), 2) AS attrition_rate_pct
FROM dw.fact_headcount_monthly WHERE headcount_start >= 10;

CREATE OR REPLACE VIEW m05_attrition_rate_rolling_12m AS
SELECT department_id, month, ROUND(100.0 * exits_12m / NULLIF(avg_hc_12m, 0), 2) AS attrition_rolling_12m_pct
FROM (
  SELECT department_id, month_start_date AS month,
         SUM(exits) OVER w AS exits_12m, AVG(headcount_end) OVER w AS avg_hc_12m, COUNT(*) OVER w AS n_months
  FROM dw.fact_headcount_monthly
  WINDOW w AS (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)
) WHERE n_months = 12 AND avg_hc_12m >= 10;

CREATE OR REPLACE VIEW m06_voluntary_attrition_rate AS
SELECT department_id, month, ROUND(100.0 * vol_12m / NULLIF(avg_hc_12m, 0), 2) AS voluntary_attrition_pct
FROM (
  SELECT department_id, month_start_date AS month,
         SUM(voluntary_exits) OVER w AS vol_12m, AVG(headcount_end) OVER w AS avg_hc_12m, COUNT(*) OVER w AS n_months
  FROM dw.fact_headcount_monthly
  WINDOW w AS (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)
) WHERE n_months = 12 AND avg_hc_12m >= 10;

CREATE OR REPLACE VIEW m07_gross_pay AS
SELECT department_id, CAST(period_end_date AS DATE) AS month_end, SUM(gross_pay) AS gross_pay
FROM dw.fact_payroll GROUP BY 1, 2 HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW m08_net_pay AS
SELECT department_id, CAST(period_end_date AS DATE) AS month_end, SUM(net_pay) AS net_pay
FROM dw.fact_payroll GROUP BY 1, 2 HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW m09_payroll_cost AS
SELECT department_id, CAST(period_end_date AS DATE) AS month_end, SUM(employer_cost) AS payroll_cost
FROM dw.fact_payroll GROUP BY 1, 2 HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW m10_cost_per_head AS
SELECT department_id, CAST(period_end_date AS DATE) AS month_end,
       ROUND(SUM(employer_cost) / COUNT(DISTINCT employee_id), 2) AS cost_per_head
FROM dw.fact_payroll GROUP BY 1, 2 HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW m11_overtime_share AS
SELECT department_id, CAST(period_end_date AS DATE) AS month_end,
       ROUND(100.0 * SUM(overtime_pay) / NULLIF(SUM(employer_cost), 0), 2) AS overtime_share_pct
FROM dw.fact_payroll GROUP BY 1, 2 HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW m12_variable_pay_share AS
SELECT department_id, CAST(period_end_date AS DATE) AS month_end,
       ROUND(100.0 * SUM(variable_pay) / NULLIF(SUM(gross_pay), 0), 2) AS variable_pay_share_pct
FROM dw.fact_payroll GROUP BY 1, 2 HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW m13_attendance_rate AS
SELECT department_id, CAST(period_end_date AS DATE) AS month_end,
       ROUND((SUM(present_days) + 0.5 * SUM(half_days_unpaid)) / NULLIF(SUM(scheduled_days), 0), 4) AS attendance_rate
FROM dw.fact_attendance_monthly GROUP BY 1, 2 HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW m14_late_arrival_rate AS
SELECT department_id, CAST(period_end_date AS DATE) AS month_end,
       ROUND(SUM(late_arrivals) / NULLIF(SUM(present_days), 0), 4) AS late_arrival_rate
FROM dw.fact_attendance_monthly GROUP BY 1, 2 HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW m15_leave_without_pay_days AS
SELECT department_id, CAST(period_end_date AS DATE) AS month_end, SUM(lop_days) AS lop_days
FROM dw.fact_payroll GROUP BY 1, 2 HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW m16_revenue AS
SELECT account_code, date_trunc('month', CAST(entry_date AS DATE)) AS month,
       -SUM(signed_amount_debit_positive) AS revenue
FROM dw.fact_ledger
WHERE CAST(account_code AS VARCHAR) BETWEEN '4001' AND '4004'
GROUP BY 1, 2;

CREATE OR REPLACE VIEW m17_net_profit AS
SELECT date_trunc('month', CAST(entry_date AS DATE)) AS month,
       -SUM(signed_amount_debit_positive) AS net_profit
FROM dw.fact_ledger
WHERE CAST(account_code AS VARCHAR) LIKE '4%' OR CAST(account_code AS VARCHAR) LIKE '5%'
GROUP BY 1;

CREATE OR REPLACE VIEW m18_operating_margin AS
SELECT p.month, p.net_profit, r.revenue,
       ROUND(100.0 * p.net_profit / NULLIF(r.revenue, 0), 2) AS operating_margin_pct
FROM m17_net_profit p
JOIN (SELECT month, SUM(revenue) AS revenue FROM m16_revenue GROUP BY 1) r USING (month);

CREATE OR REPLACE VIEW m19_payroll_pct_of_revenue AS
SELECT c.month, c.payroll_cost, r.revenue,
       ROUND(100.0 * c.payroll_cost / NULLIF(r.revenue, 0), 2) AS payroll_pct_of_revenue
FROM (SELECT date_trunc('month', CAST(period_end_date AS DATE)) AS month, SUM(employer_cost) AS payroll_cost
      FROM dw.fact_payroll GROUP BY 1) c
JOIN (SELECT month, SUM(revenue) AS revenue FROM m16_revenue GROUP BY 1) r USING (month);

CREATE OR REPLACE VIEW m20_dso AS
WITH m AS (SELECT DISTINCT CAST(month_end_date AS DATE) AS month_end FROM dw.dim_date),
r AS (
  SELECT m.month_end,
    (SELECT COALESCE(SUM(total_amount), 0) FROM dw.fact_invoice i WHERE CAST(i.invoice_date AS DATE) <= m.month_end)
    - (SELECT COALESCE(SUM(amount), 0) FROM dw.fact_invoice_payment p WHERE CAST(p.payment_date AS DATE) <= m.month_end) AS receivables,
    (SELECT COALESCE(SUM(total_amount), 0) FROM dw.fact_invoice i
      WHERE CAST(i.invoice_date AS DATE) > m.month_end - INTERVAL 90 DAY
        AND CAST(i.invoice_date AS DATE) <= m.month_end) AS revenue_90d
  FROM m)
SELECT month_end, receivables, revenue_90d, ROUND(receivables / NULLIF(revenue_90d, 0) * 90, 1) AS dso_days
FROM r WHERE revenue_90d > 0;

CREATE OR REPLACE VIEW m21_overdue_receivables AS
SELECT client_id, SUM(balance_due) AS overdue_receivables
FROM dw.fact_invoice
WHERE days_past_due_at_cutoff > 0 AND UPPER(status) NOT IN ('DRAFT', 'CANCELLED')
GROUP BY 1;

CREATE OR REPLACE VIEW m22_task_completion_rate AS
SELECT team_id, sprint_id,
       ROUND(COUNT(*) FILTER (WHERE status = 'Done') * 1.0 / NULLIF(COUNT(*) FILTER (WHERE status <> 'Cancelled'), 0), 4) AS completion_rate
FROM dw.fact_task GROUP BY 1, 2 HAVING COUNT(*) >= 5;

CREATE OR REPLACE VIEW m23_on_time_delivery_rate AS
SELECT team_id, sprint_id,
       ROUND(COUNT(*) FILTER (WHERE CAST(completed_on_time AS VARCHAR) IN ('Y', 'true', 'True', '1')) * 1.0
             / NULLIF(COUNT(*) FILTER (WHERE status = 'Done'), 0), 4) AS on_time_rate
FROM dw.fact_task GROUP BY 1, 2 HAVING COUNT(*) >= 5;

CREATE OR REPLACE VIEW m24_velocity AS
SELECT team_id, sprint_id, SUM(story_points) AS velocity
FROM dw.fact_task WHERE status = 'Done' GROUP BY 1, 2;

CREATE OR REPLACE VIEW m25_average_cycle_time AS
SELECT team_id, sprint_id,
       ROUND(AVG(date_diff('day', CAST(started_date AS DATE), CAST(completed_date AS DATE))), 2) AS avg_cycle_days
FROM dw.fact_task WHERE completed_date IS NOT NULL AND started_date IS NOT NULL
GROUP BY 1, 2 HAVING COUNT(*) >= 5;

CREATE OR REPLACE VIEW m26_anomaly_flag_rate AS
SELECT source_dataset, period AS month,
       ROUND(COUNT(*) FILTER (WHERE CAST(flagged AS VARCHAR) IN ('Y', 'true', 'True', '1')) * 1.0 / COUNT(*), 4) AS flag_rate
FROM dw.fact_anomaly GROUP BY 1, 2;

CREATE OR REPLACE VIEW m27_high_risk_share AS
SELECT department_id,
       ROUND(COUNT(*) FILTER (WHERE risk_band = 'High') * 1.0 / COUNT(*), 4) AS high_risk_share
FROM dw.fact_attrition_risk
WHERE as_of_date = (SELECT MAX(as_of_date) FROM dw.fact_attrition_risk)
GROUP BY 1 HAVING COUNT(*) >= 10;

CREATE OR REPLACE VIEW m28_forecast_error_mape AS
WITH a AS (
  SELECT CAST(department_id AS VARCHAR) AS department_id, CAST(month_start_date AS DATE) AS month, headcount_end AS actual
  FROM dw.fact_headcount_monthly
  UNION ALL
  SELECT 'ALL', CAST(month_start_date AS DATE), SUM(headcount_end)
  FROM dw.fact_headcount_monthly GROUP BY 2
)
SELECT CAST(f.department_id AS VARCHAR) AS department_id, CAST(f.forecast_month AS DATE) AS month,
       f.forecast_value, a.actual,
       ROUND(ABS(a.actual - f.forecast_value) / NULLIF(a.actual, 0) * 100, 2) AS abs_pct_error,
       CASE WHEN a.actual IS NULL THEN 'awaiting actuals' ELSE 'scored' END AS status
FROM dw.fact_forecast f
LEFT JOIN a ON a.department_id = CAST(f.department_id AS VARCHAR) AND a.month = CAST(f.forecast_month AS DATE)
WHERE f.metric = 'headcount_end';