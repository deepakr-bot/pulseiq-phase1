-- Traffic lights: targets come from kpi_targets; the amber band is a chosen rule (see the rule column)
CREATE OR REPLACE VIEW dw.v_kpi_status AS
WITH t AS (SELECT strftime(CAST(month AS DATE), '%Y-%m') AS month, department_id, attendance_rate_target,
                  overtime_share_target_pct, attrition_monthly_target_pct, task_completion_target_pct
           FROM dw.kpi_targets),
att AS (SELECT department_id, strftime(month_end, '%Y-%m') AS month, attendance_rate AS v FROM main.m13_attendance_rate),
ot AS (SELECT department_id, strftime(month_end, '%Y-%m') AS month, overtime_share_pct AS v FROM main.m11_overtime_share),
ar AS (SELECT department_id, strftime(month, '%Y-%m') AS month, attrition_rate_pct AS v FROM main.m04_attrition_rate_monthly),
tc AS (
  SELECT CAST(tm."department_id" AS VARCHAR) AS department_id, strftime(CAST(sp."start_date" AS DATE), '%Y-%m') AS month,
         100.0 * COUNT(*) FILTER (WHERE f.status = 'Done')
               / NULLIF(COUNT(*) FILTER (WHERE f.status <> 'Cancelled'), 0) AS v
  FROM dw.fact_task f
  JOIN dw.dim_team tm ON CAST(f.team_id AS VARCHAR) = CAST(tm."team_id" AS VARCHAR)
  JOIN dw.dim_sprint sp ON CAST(f.sprint_id AS VARCHAR) = CAST(sp."sprint_id" AS VARCHAR)
  GROUP BY 1, 2),
k AS (
  SELECT 'Attendance rate' AS kpi, t.department_id, t.month, att.v AS actual, t.attendance_rate_target AS target,
         'higher' AS direction, 0.02 AS band,
         'Higher is better. Green: at or above target. Amber: up to 0.02 below target. Red: more than 0.02 below target. Actual = metric M13.' AS rule
  FROM t LEFT JOIN att ON att.department_id = t.department_id AND att.month = t.month
  UNION ALL
  SELECT 'Overtime share', t.department_id, t.month, ot.v, t.overtime_share_target_pct, 'lower', 0.5,
         'Lower is better. Green: at or below target. Amber: up to 0.5 points above target. Red: more than 0.5 points above target. Actual = metric M11.'
  FROM t LEFT JOIN ot ON ot.department_id = t.department_id AND ot.month = t.month
  UNION ALL
  SELECT 'Monthly attrition', t.department_id, t.month, ar.v, t.attrition_monthly_target_pct, 'lower', 0.5,
         'Lower is better. Green: at or below target. Amber: up to 0.5 points above target. Red: more than 0.5 points above target. Actual = metric M04 (groups of 10 or more only).'
  FROM t LEFT JOIN ar ON ar.department_id = t.department_id AND ar.month = t.month
  UNION ALL
  SELECT 'Task completion', t.department_id, t.month, tc.v, t.task_completion_target_pct, 'higher', 5.0,
         'Higher is better. Green: at or above target. Amber: up to 5.0 points below target. Red: more than 5.0 points below target. Actual = tasks Done / tasks not cancelled, by department and sprint start month.'
  FROM t LEFT JOIN tc ON tc.department_id = t.department_id AND tc.month = t.month
)
SELECT k.kpi, k.department_id AS department_id, COALESCE(d.department_name, k.department_id) AS department,
       k.month, k.actual, k.target,
       CASE WHEN k.actual IS NULL OR k.target IS NULL THEN 'Grey'
            WHEN k.direction = 'higher' THEN
                 CASE WHEN k.actual >= k.target THEN 'Green' WHEN k.actual >= k.target - k.band THEN 'Amber' ELSE 'Red' END
            ELSE CASE WHEN k.actual <= k.target THEN 'Green' WHEN k.actual <= k.target + k.band THEN 'Amber' ELSE 'Red' END
       END AS status,
       k.rule
FROM k LEFT JOIN dw.dim_department d ON d.department_id = k.department_id;
