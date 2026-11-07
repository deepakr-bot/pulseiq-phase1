import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("Dashboard source (m01_headcount, Sep 2026):",
      con.sql("SELECT SUM(headcount) FROM m01_headcount WHERE month = '2026-09-01'").fetchone()[0])

print("Raw total in the warehouse (all departments):",
      con.sql("SELECT SUM(headcount_end) FROM dw.fact_headcount_monthly WHERE month_start_date = '2026-09-01'").fetchone()[0])

print("Departments hidden because they have fewer than 5 people:")
print(con.sql("SELECT department_id, headcount_end FROM dw.fact_headcount_monthly WHERE month_start_date = '2026-09-01' AND headcount_end < 5").df())