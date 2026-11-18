# check_headcount.py
from pathlib import Path
import duckdb

DB = Path(__file__).resolve().parents[2] / "pulseiq.duckdb"
con = duckdb.connect(str(DB), read_only=True)

print("Where the objects live:")
for row in con.execute(
    "SELECT table_schema, table_name FROM information_schema.tables "
    "WHERE table_name IN ('m01_headcount', 'fact_headcount_monthly')"
).fetchall():
    print(" ", row)

print("\nLatest-month sum in each schema:")
for schema in [r[0] for r in con.execute(
    "SELECT DISTINCT table_schema FROM information_schema.tables WHERE table_name='m01_headcount'"
).fetchall()]:
    total = con.execute(
        f"SELECT SUM(headcount) FROM {schema}.m01_headcount "
        f"WHERE month = (SELECT MAX(month) FROM {schema}.m01_headcount)"
    ).fetchone()[0]
    print(f"  {schema}.m01_headcount -> {total}")

con.close()