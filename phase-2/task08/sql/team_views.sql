-- RULES (also shown on the dashboard page)
-- Velocity   = story points of tasks with status Done, per sprint.
-- Cycle time = days from started date (created date if no started date) to done date,
--              Done tasks only; negative or missing dates are ignored.
-- On-time    = Done tasks finished on or before the due date / Done tasks that have a due date.
-- Cancelled  = excluded from every metric (planned, velocity, cycle time, on-time, blocked,
--              reopened). Only the count of cancelled tasks is shown, for context.
-- Reopened and blocked tasks are counted once per task and shown as a share of planned tasks.

CREATE OR REPLACE VIEW dw.v_task_clean AS
SELECT t."task_id" AS task_id,
       CAST(t."team_id" AS VARCHAR) AS team_id,
       COALESCE(CAST(tm."team_name" AS VARCHAR), CAST(t."team_id" AS VARCHAR)) AS team,
       CAST(t."sprint_id" AS VARCHAR) AS sprint_id,
       COALESCE(CAST(sp."sprint_name" AS VARCHAR), CAST(t."sprint_id" AS VARCHAR)) AS sprint,
       TRY_CAST(sp."start_date" AS DATE) AS sprint_start,
       CASE WHEN UPPER(CAST(t."status" AS VARCHAR)) LIKE '%CANCEL%' THEN 'Cancelled' WHEN UPPER(CAST(t."status" AS VARCHAR)) LIKE '%DONE%' OR UPPER(CAST(t."status" AS VARCHAR)) LIKE '%COMPLET%' OR UPPER(CAST(t."status" AS VARCHAR)) LIKE '%CLOSED%' OR UPPER(CAST(t."status" AS VARCHAR)) LIKE '%RESOLV%' THEN 'Done' ELSE 'Open' END AS status_group,
       COALESCE(TRY_CAST(t."story_points" AS DOUBLE), 0) AS points,
       TRY_CAST(t."created_date" AS DATE) AS created_date,
       TRY_CAST(t."started_date" AS DATE) AS started_date,
       TRY_CAST(t."completed_date" AS DATE) AS done_date,
       TRY_CAST(t."due_date" AS DATE) AS due_date,
       CASE WHEN (CASE WHEN COALESCE(CAST(t."reopened_count" AS DOUBLE), 0) > 0 THEN 1 ELSE 0 END) = 1 OR UPPER(CAST(t."status" AS VARCHAR)) LIKE '%REOPEN%' THEN 1 ELSE 0 END AS reopened,
       CASE WHEN 0 = 1 OR UPPER(CAST(t."status" AS VARCHAR)) LIKE '%BLOCK%' THEN 1 ELSE 0 END AS blocked
FROM dw.fact_task t
LEFT JOIN dw.dim_team tm ON CAST(t."team_id" AS VARCHAR) = CAST(tm."team_id" AS VARCHAR)
LEFT JOIN dw.dim_sprint sp ON CAST(t."sprint_id" AS VARCHAR) = CAST(sp."sprint_id" AS VARCHAR);

CREATE OR REPLACE VIEW dw.v_task_metrics AS
SELECT *,
  CASE WHEN status_group = 'Done' AND done_date IS NOT NULL
        AND COALESCE(started_date, created_date) IS NOT NULL
        AND DATEDIFF('day', COALESCE(started_date, created_date), done_date) >= 0
       THEN DATEDIFF('day', COALESCE(started_date, created_date), done_date) END AS cycle_days,
  CASE WHEN status_group = 'Done' AND done_date IS NOT NULL AND due_date IS NOT NULL
       THEN CASE WHEN done_date <= due_date THEN 1 ELSE 0 END END AS on_time
FROM dw.v_task_clean;

CREATE OR REPLACE VIEW dw.v_team_sprint AS
SELECT team, sprint_id, sprint, MIN(sprint_start) AS sprint_start,
  COUNT(*) FILTER (WHERE status_group <> 'Cancelled') AS planned,
  COUNT(*) FILTER (WHERE status_group = 'Cancelled') AS cancelled,
  COUNT(*) FILTER (WHERE status_group = 'Done') AS done,
  COALESCE(SUM(points) FILTER (WHERE status_group = 'Done'), 0) AS points_done,
  COALESCE(SUM(cycle_days), 0) AS cycle_sum,
  COUNT(cycle_days) AS cycle_n,
  COUNT(on_time) AS due_done,
  COALESCE(SUM(on_time), 0) AS on_time_done,
  COALESCE(SUM(blocked) FILTER (WHERE status_group <> 'Cancelled'), 0) AS blocked,
  COALESCE(SUM(reopened) FILTER (WHERE status_group <> 'Cancelled'), 0) AS reopened
FROM dw.v_task_metrics
GROUP BY team, sprint_id, sprint;

CREATE OR REPLACE VIEW dw.v_team_overall AS
SELECT team,
  COUNT(DISTINCT sprint_id) FILTER (WHERE status_group <> 'Cancelled') AS sprints,
  COUNT(*) FILTER (WHERE status_group <> 'Cancelled') AS planned,
  COUNT(*) FILTER (WHERE status_group = 'Cancelled') AS cancelled,
  COUNT(*) FILTER (WHERE status_group = 'Done') AS done,
  COALESCE(SUM(points) FILTER (WHERE status_group = 'Done'), 0) AS points_done,
  COALESCE(SUM(cycle_days), 0) AS cycle_sum,
  COUNT(cycle_days) AS cycle_n,
  COUNT(on_time) AS due_done,
  COALESCE(SUM(on_time), 0) AS on_time_done,
  COALESCE(SUM(blocked) FILTER (WHERE status_group <> 'Cancelled'), 0) AS blocked,
  COALESCE(SUM(reopened) FILTER (WHERE status_group <> 'Cancelled'), 0) AS reopened
FROM dw.v_task_metrics
GROUP BY team;

CREATE OR REPLACE VIEW dw.v8_velocity AS
SELECT team, sprint, sprint_start, points_done AS velocity_points, done AS tasks_done
FROM dw.v_team_sprint;

CREATE OR REPLACE VIEW dw.v8_cycle_time AS
SELECT team, sprint, sprint_start, cycle_sum * 1.0 / NULLIF(cycle_n, 0) AS avg_cycle_days,
       cycle_n AS tasks_measured
FROM dw.v_team_sprint;

CREATE OR REPLACE VIEW dw.v8_on_time_rate AS
SELECT team, sprint, sprint_start, on_time_done * 1.0 / NULLIF(due_done, 0) AS on_time_rate,
       due_done AS tasks_with_due_date
FROM dw.v_team_sprint;
