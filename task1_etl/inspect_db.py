import duckdb

con = duckdb.connect("pulseiq.duckdb")

print("=== TABLES ===")
for (t,) in con.execute(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema='raw' ORDER BY 1").fetchall():
    print(t)

print("\n=== DATA CONTRACTS (columns) ===")
print(con.execute("DESCRIBE raw.data_contracts").df().to_string(index=False))

print("\n=== DATA CONTRACTS (first 15 rows) ===")
print(con.execute("SELECT * FROM raw.data_contracts LIMIT 15").df().to_string(index=False))