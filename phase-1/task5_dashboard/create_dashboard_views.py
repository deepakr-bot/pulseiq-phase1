import duckdb
con = duckdb.connect("pulseiq.duckdb")
for s in open("dashboard_views.sql").read().split(";"):
    if s.strip():
        con.sql(s)
for v in ["v5_department", "v5_company_attrition_12m", "v5_headcount_by_location_tier", "v5_headcount_by_work_mode"]:
    print(v, con.sql(f"SELECT COUNT(*) FROM {v}").fetchone()[0], "rows")