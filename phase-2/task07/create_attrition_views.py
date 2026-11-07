import duckdb
con = duckdb.connect("pulseiq.duckdb")
con.execute(open("sql/attrition_views.sql").read())
for v in ["v_exits_monthly", "v_exit_tenure", "v_risk_by_dept", "v_risk_reasons"]:
    print("\n", v)
    print(con.sql(f"SELECT * FROM dw.{v} LIMIT 5").df().to_string())
con.close()