import json
from team_common import connect, detect, date_sql, flag_sql

con = connect(read_only=False)
m, types = detect(con)
ft, tm, sp = types["ft"], types["tm"], types["sp"]

print("Column mapping used:")
for k, v in m.items():
    print(f"  {k:14s} -> {v}")

missing = [k for k in ["team", "sprint", "status", "team_dim_id", "sprint_dim_id"] if m[k] is None]
if missing:
    print("\nSTOP: could not find", missing, "- paste the output of check_team_data.py here.")
    raise SystemExit(1)


def fdate(key):
    col = m[key]
    return date_sql(col, ft[col], "t") if col else "CAST(NULL AS DATE)"


status_up = f'UPPER(CAST(t."{m["status"]}" AS VARCHAR))'
status_group = (
    f"CASE WHEN {status_up} LIKE '%CANCEL%' THEN 'Cancelled' "
    f"WHEN {status_up} LIKE '%DONE%' OR {status_up} LIKE '%COMPLET%' "
    f"OR {status_up} LIKE '%CLOSED%' OR {status_up} LIKE '%RESOLV%' THEN 'Done' "
    f"ELSE 'Open' END"
)
points = f'COALESCE(TRY_CAST(t."{m["points"]}" AS DOUBLE), 0)' if m["points"] else "1.0"
rf = flag_sql(m["reopened"], ft.get(m["reopened"], ""), "t")
bf = flag_sql(m["blocked"], ft.get(m["blocked"], ""), "t")
reopened = f"CASE WHEN {rf} = 1 OR {status_up} LIKE '%REOPEN%' THEN 1 ELSE 0 END"
blocked = f"CASE WHEN {bf} = 1 OR {status_up} LIKE '%BLOCK%' THEN 1 ELSE 0 END"

team_id = f'CAST(t."{m["team"]}" AS VARCHAR)'
team_name = (f'COALESCE(CAST(tm."{m["team_name"]}" AS VARCHAR), {team_id})'
             if m["team_name"] else team_id)
sprint_id = f'CAST(t."{m["sprint"]}" AS VARCHAR)'
sprint_name = (f'COALESCE(CAST(sp."{m["sprint_name"]}" AS VARCHAR), {sprint_id})'
               if m["sprint_name"] else sprint_id)
sprint_start = (date_sql(m["sprint_start"], sp[m["sprint_start"]], "sp")
                if m["sprint_start"] else "CAST(NULL AS DATE)")
task_id = f't."{m["task_id"]}"' if m["task_id"] else "NULL"

RULES = """-- RULES (also shown on the dashboard page)
-- Velocity   = story points of tasks with status Done, per sprint.
-- Cycle time = days from started date (created date if no started date) to done date,
--              Done tasks only; negative or missing dates are ignored.
-- On-time    = Done tasks finished on or before the due date / Done tasks that have a due date.
-- Cancelled  = excluded from every metric (planned, velocity, cycle time, on-time, blocked,
--              reopened). Only the count of cancelled tasks is shown, for context.
-- Reopened and blocked tasks are counted once per task and shown as a share of planned tasks.
"""

stmts = []
stmts.append(f"""CREATE OR REPLACE VIEW dw.v_task_clean AS
SELECT {task_id} AS task_id,
       {team_id} AS team_id,
       {team_name} AS team,
       {sprint_id} AS sprint_id,
       {sprint_name} AS sprint,
       {sprint_start} AS sprint_start,
       {status_group} AS status_group,
       {points} AS points,
       {fdate("created")} AS created_date,
       {fdate("started")} AS started_date,
       {fdate("done")} AS done_date,
       {fdate("due")} AS due_date,
       {reopened} AS reopened,
       {blocked} AS blocked
FROM dw.fact_task t
LEFT JOIN dw.dim_team tm ON {team_id} = CAST(tm."{m["team_dim_id"]}" AS VARCHAR)
LEFT JOIN dw.dim_sprint sp ON {sprint_id} = CAST(sp."{m["sprint_dim_id"]}" AS VARCHAR)""")

stmts.append("""CREATE OR REPLACE VIEW dw.v_task_metrics AS
SELECT *,
  CASE WHEN status_group = 'Done' AND done_date IS NOT NULL
        AND COALESCE(started_date, created_date) IS NOT NULL
        AND DATEDIFF('day', COALESCE(started_date, created_date), done_date) >= 0
       THEN DATEDIFF('day', COALESCE(started_date, created_date), done_date) END AS cycle_days,
  CASE WHEN status_group = 'Done' AND done_date IS NOT NULL AND due_date IS NOT NULL
       THEN CASE WHEN done_date <= due_date THEN 1 ELSE 0 END END AS on_time
FROM dw.v_task_clean""")

AGG = """  COUNT(*) FILTER (WHERE status_group <> 'Cancelled') AS planned,
  COUNT(*) FILTER (WHERE status_group = 'Cancelled') AS cancelled,
  COUNT(*) FILTER (WHERE status_group = 'Done') AS done,
  COALESCE(SUM(points) FILTER (WHERE status_group = 'Done'), 0) AS points_done,
  COALESCE(SUM(cycle_days), 0) AS cycle_sum,
  COUNT(cycle_days) AS cycle_n,
  COUNT(on_time) AS due_done,
  COALESCE(SUM(on_time), 0) AS on_time_done,
  COALESCE(SUM(blocked) FILTER (WHERE status_group <> 'Cancelled'), 0) AS blocked,
  COALESCE(SUM(reopened) FILTER (WHERE status_group <> 'Cancelled'), 0) AS reopened"""

stmts.append(f"""CREATE OR REPLACE VIEW dw.v_team_sprint AS
SELECT team, sprint_id, sprint, MIN(sprint_start) AS sprint_start,
{AGG}
FROM dw.v_task_metrics
GROUP BY team, sprint_id, sprint""")

stmts.append(f"""CREATE OR REPLACE VIEW dw.v_team_overall AS
SELECT team,
  COUNT(DISTINCT sprint_id) FILTER (WHERE status_group <> 'Cancelled') AS sprints,
{AGG}
FROM dw.v_task_metrics
GROUP BY team""")

stmts.append("""CREATE OR REPLACE VIEW dw.v8_velocity AS
SELECT team, sprint, sprint_start, points_done AS velocity_points, done AS tasks_done
FROM dw.v_team_sprint""")
stmts.append("""CREATE OR REPLACE VIEW dw.v8_cycle_time AS
SELECT team, sprint, sprint_start, cycle_sum * 1.0 / NULLIF(cycle_n, 0) AS avg_cycle_days,
       cycle_n AS tasks_measured
FROM dw.v_team_sprint""")
stmts.append("""CREATE OR REPLACE VIEW dw.v8_on_time_rate AS
SELECT team, sprint, sprint_start, on_time_done * 1.0 / NULLIF(due_done, 0) AS on_time_rate,
       due_done AS tasks_with_due_date
FROM dw.v_team_sprint""")

for s in stmts:
    con.execute(s)

with open("sql/team_views.sql", "w", encoding="utf-8") as f:
    f.write(RULES + "\n" + ";\n\n".join(stmts) + ";\n")

rules = {
    "cycle_start": "started date" if m["started"] else ("created date" if m["created"] else "not available"),
    "points_column": m["points"],
    "blocked_column": m["blocked"],
    "reopened_column": m["reopened"],
}
with open("team_rules.json", "w", encoding="utf-8") as f:
    json.dump(rules, f, indent=2)

print("\nSTATUS GROUPS")
print(con.sql("SELECT status_group, COUNT(*) n FROM dw.v_task_clean GROUP BY 1 ORDER BY 2 DESC").df())
print("\nSTATUS VALUES SEEN (check the grouping is right)")
print(con.sql(f'SELECT "{m["status"]}" AS status, COUNT(*) n FROM dw.fact_task GROUP BY 1 ORDER BY 2 DESC').df())
n_raw = con.sql("SELECT COUNT(*) FROM dw.fact_task").fetchone()[0]
n_view = con.sql("SELECT COUNT(*) FROM dw.v_task_clean").fetchone()[0]
n_ts = con.sql("SELECT SUM(planned + cancelled) FROM dw.v_team_sprint").fetchone()[0]
print(f"\nROW CHECK: fact_task={n_raw}, v_task_clean={n_view}, v_team_sprint total={n_ts} (all three must be equal)")
print("\nSAMPLE")
print(con.sql("SELECT * FROM dw.v_team_overall ORDER BY team LIMIT 5").df().to_string())
con.close()