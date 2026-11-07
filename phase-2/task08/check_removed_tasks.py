import duckdb
import pandas as pd
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 60)

con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("QUARANTINE columns")
print(con.sql("DESCRIBE main.quarantine").df()[["column_name", "column_type"]].to_string(index=False))
print("\nQUARANTINE sample")
print(con.sql("SELECT * FROM main.quarantine LIMIT 3").df().to_string())

print("\nThe 20 rows in raw but not in dw (task data only, no people)")
print(con.sql("""
    SELECT r.task_id, r.team_id, r.sprint_id, r.status, r.story_points,
           r.created_date, r.started_date, r.completed_date, r.due_date
    FROM raw.fact_task r
    WHERE r.task_id NOT IN (SELECT task_id FROM dw.fact_task)
    ORDER BY r.task_id""").df().to_string(index=False))