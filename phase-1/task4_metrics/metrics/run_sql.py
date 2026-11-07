import duckdb, sys
con = duckdb.connect("pulseiq.duckdb")
for stmt in open(sys.argv[1]).read().split(";"):
    if stmt.strip():
        r = con.sql(stmt)
        if r is not None:
            print(r.df().to_string())