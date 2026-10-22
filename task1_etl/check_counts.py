import duckdb

con = duckdb.connect("pulseiq.duckdb")
for s, t in con.execute(
    "SELECT table_schema, table_name FROM information_schema.tables "
    "WHERE table_schema='raw' ORDER BY 2").fetchall():
    n = con.execute(f'SELECT COUNT(*) FROM {s}."{t}"').fetchone()[0]
    print(f"{s}.{t}: {n}")