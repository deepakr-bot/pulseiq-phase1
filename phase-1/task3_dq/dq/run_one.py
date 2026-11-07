import duckdb, sys

con = duckdb.connect("pulseiq.duckdb")
sql = open(sys.argv[1]).read()
df = con.sql(sql).df()
print(len(df), "bad rows")
print(df.head(10).to_string())