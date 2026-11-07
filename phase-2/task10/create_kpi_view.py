import os

from budget_common import connect, table_cols, find, month_sql

# Traffic-light bands (the data has targets only, so these are my rules; the page shows them)
BAND = {"att": 0.02, "ot": 0.5, "attr": 0.5, "task": 5.0}

os.makedirs("sql", exist_ok=True)
con = connect(read_only=False)

tm, sp, ft = (table_cols(con, "dw.dim_team"), table_cols(con, "dw.dim_sprint"), table_cols(con, "dw.fact_task"))
t_id, t_dep = find(tm, "team_id"), find(tm, "department_id", "dept_id")
s_id, s_start = find(sp, "sprint_id"), find(sp, "start_date", "sprint_start", "start")
print("Task completion mapping:")
print(f"  dim_team: team -> {t_id}, department -> {t_dep}")
print(f"  dim_sprint: sprint -> {s_id}, start -> {s_start}")

has_task = bool(t_id and t_dep and s_id and s_start and "team_id" in ft and "sprint_id" in ft)
tc_cte, tc_union = "", ""
if has_task:
    tc_cte = f"""tc AS (
  SELECT CAST(tm."{t_dep}" AS VARCHAR) AS department_id, {month_sql(s_start, sp[s_start], "sp")} AS month,
         100.0 * COUNT(*) FILTER (WHERE f.status = 'Done')
               / NULLIF(COUNT(*) FILTER (WHERE f.status <> 'Cancelled'), 0) AS v
  FROM dw.fact_task f
  JOIN dw.dim_team tm ON CAST(f.team_id AS VARCHAR) = CAST(tm."{t_id}" AS VARCHAR)
  JOIN dw.dim_sprint sp ON CAST(f.sprint_id AS VARCHAR) = CAST(sp."{s_id}" AS VARCHAR)
  GROUP BY 1, 2),"""
    tc_union = f"""UNION ALL
  SELECT 'Task completion', t.department_id, t.month, tc.v, t.task_completion_target_pct, 'higher', {BAND['task']},
         'Higher is better. Green: at or above target. Amber: up to {BAND['task']} points below target. Red: more than {BAND['task']} points below target. Actual = tasks Done / tasks not cancelled, by department and sprint start month.'
  FROM t LEFT JOIN tc ON tc.department_id = t.department_id AND tc.month = t.month"""
else:
    print("  -> Task completion is NOT built (no team-to-department or sprint start column found). Paste this output here.")

sql = f"""CREATE OR REPLACE VIEW dw.v_kpi_status AS
WITH t AS (SELECT strftime(CAST(month AS DATE), '%Y-%m') AS month, department_id, attendance_rate_target,
                  overtime_share_target_pct, attrition_monthly_target_pct, task_completion_target_pct
           FROM dw.kpi_targets),
att AS (SELECT department_id, strftime(month_end, '%Y-%m') AS month, attendance_rate AS v FROM main.m13_attendance_rate),
ot AS (SELECT department_id, strftime(month_end, '%Y-%m') AS month, overtime_share_pct AS v FROM main.m11_overtime_share),
ar AS (SELECT department_id, strftime(month, '%Y-%m') AS month, attrition_rate_pct AS v FROM main.m04_attrition_rate_monthly),
{tc_cte}
k AS (
  SELECT 'Attendance rate' AS kpi, t.department_id, t.month, att.v AS actual, t.attendance_rate_target AS target,
         'higher' AS direction, {BAND['att']} AS band,
         'Higher is better. Green: at or above target. Amber: up to {BAND['att']} below target. Red: more than {BAND['att']} below target. Actual = metric M13.' AS rule
  FROM t LEFT JOIN att ON att.department_id = t.department_id AND att.month = t.month
  UNION ALL
  SELECT 'Overtime share', t.department_id, t.month, ot.v, t.overtime_share_target_pct, 'lower', {BAND['ot']},
         'Lower is better. Green: at or below target. Amber: up to {BAND['ot']} points above target. Red: more than {BAND['ot']} points above target. Actual = metric M11.'
  FROM t LEFT JOIN ot ON ot.department_id = t.department_id AND ot.month = t.month
  UNION ALL
  SELECT 'Monthly attrition', t.department_id, t.month, ar.v, t.attrition_monthly_target_pct, 'lower', {BAND['attr']},
         'Lower is better. Green: at or below target. Amber: up to {BAND['attr']} points above target. Red: more than {BAND['attr']} points above target. Actual = metric M04 (groups of 10 or more only).'
  FROM t LEFT JOIN ar ON ar.department_id = t.department_id AND ar.month = t.month
  {tc_union}
)
SELECT k.kpi, k.department_id AS department_id, COALESCE(d.department_name, k.department_id) AS department,
       k.month, k.actual, k.target,
       CASE WHEN k.actual IS NULL OR k.target IS NULL THEN 'Grey'
            WHEN k.direction = 'higher' THEN
                 CASE WHEN k.actual >= k.target THEN 'Green' WHEN k.actual >= k.target - k.band THEN 'Amber' ELSE 'Red' END
            ELSE CASE WHEN k.actual <= k.target THEN 'Green' WHEN k.actual <= k.target + k.band THEN 'Amber' ELSE 'Red' END
       END AS status,
       k.rule
FROM k LEFT JOIN dw.dim_department d ON d.department_id = k.department_id"""
con.execute(sql)
con.execute("CREATE OR REPLACE VIEW main.v10_kpi_status AS SELECT * FROM dw.v_kpi_status")
with open("sql/kpi_views.sql", "w", encoding="utf-8") as f:
    f.write("-- Traffic lights: targets come from kpi_targets; the amber band is a chosen rule (see the rule column)\n"
            + sql + ";\n")

print("\nStatus by KPI (department-months)")
print(con.sql("""SELECT kpi, status, COUNT(*) AS n FROM dw.v_kpi_status GROUP BY 1, 2 ORDER BY 1, 2""").df().to_string(index=False))
print("\nGrey rows: where and why")
print(con.sql("""SELECT kpi, department,
    SUM(CASE WHEN actual IS NULL THEN 1 ELSE 0 END) AS no_data, SUM(CASE WHEN target IS NULL THEN 1 ELSE 0 END) AS no_target
    FROM dw.v_kpi_status WHERE status = 'Grey' GROUP BY 1, 2 ORDER BY 1, 2""").df().to_string(index=False))
print("\nSaved sql/kpi_views.sql")
con.close()