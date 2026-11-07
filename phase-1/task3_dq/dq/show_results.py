import duckdb
con = duckdb.connect("pulseiq.duckdb")
print(con.sql("SELECT * FROM dq_results ORDER BY check_id").df().to_string())