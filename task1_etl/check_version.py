import duckdb
con = duckdb.connect("pulseiq.duckdb")
print(con.execute("SELECT model_version, COUNT(*) AS n FROM raw.fact_anomaly GROUP BY 1").df())