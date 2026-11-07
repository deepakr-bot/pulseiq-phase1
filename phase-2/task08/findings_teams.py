import duckdb
import pandas as pd

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\n1) Company totals")
print(con.sql("""SELECT SUM(planned) planned, SUM(cancelled) cancelled, SUM(done) done,
  ROUND(SUM(points_done) / NULLIF((SELECT COUNT(DISTINCT sprint_id) FROM dw.v_team_sprint), 0), 1) AS points_per_sprint,
  ROUND(SUM(cycle_sum) * 1.0 / NULLIF(SUM(cycle_n), 0), 1) AS avg_cycle_days,
  ROUND(SUM(on_time_done) * 100.0 / NULLIF(SUM(due_done), 0), 1) AS on_time_pct,
  ROUND(SUM(blocked) * 100.0 / NULLIF(SUM(planned), 0), 1) AS blocked_pct,
  ROUND(SUM(reopened) * 100.0 / NULLIF(SUM(planned), 0), 1) AS reopened_pct
  FROM dw.v_team_sprint""").df().to_string(index=False))

to = con.sql("""SELECT team, sprints, planned, cancelled, done, points_done,
  ROUND(points_done * 1.0 / NULLIF(sprints, 0), 1) AS velocity_per_sprint,
  ROUND(points_done * 1.0 / NULLIF(done, 0), 1) AS points_per_task,
  ROUND(cycle_sum * 1.0 / NULLIF(cycle_n, 0), 1) AS avg_cycle_days,
  ROUND(on_time_done * 100.0 / NULLIF(due_done, 0), 1) AS on_time_pct,
  ROUND(blocked * 100.0 / NULLIF(planned, 0), 1) AS blocked_pct,
  ROUND(reopened * 100.0 / NULLIF(planned, 0), 1) AS reopened_pct
  FROM dw.v_team_overall""").df()

print("\n2) Teams ranked by velocity per sprint")
print(to.sort_values("velocity_per_sprint", ascending=False).to_string(index=False))

print("\n3) Best on-time vs worst on-time")
print(to.sort_values("on_time_pct", ascending=False)[["team", "on_time_pct", "avg_cycle_days"]].to_string(index=False))

print("\n4) Highest reopened and blocked share")
print(to.sort_values("reopened_pct", ascending=False)[["team", "reopened_pct", "blocked_pct", "velocity_per_sprint"]].to_string(index=False))

print("\n5) Do fast teams reopen more? Correlation velocity vs reopened %:",
      round(to["velocity_per_sprint"].corr(to["reopened_pct"]), 2))

sp = con.sql("""SELECT sprint, MIN(sprint_start) AS sprint_start, SUM(planned) planned, SUM(done) done,
  SUM(points_done) points,
  ROUND(SUM(on_time_done) * 100.0 / NULLIF(SUM(due_done), 0), 1) AS on_time_pct,
  ROUND(SUM(blocked) * 100.0 / NULLIF(SUM(planned), 0), 1) AS blocked_pct,
  ROUND(SUM(reopened) * 100.0 / NULLIF(SUM(planned), 0), 1) AS reopened_pct
  FROM dw.v_team_sprint GROUP BY sprint, sprint_id""").df()
print("\n6) Five sprints with the lowest on-time rate")
print(sp.sort_values("on_time_pct").head(5).to_string(index=False))
print("\n7) Five sprints with the highest blocked share")
print(sp.sort_values("blocked_pct", ascending=False).head(5).to_string(index=False))
con.close()