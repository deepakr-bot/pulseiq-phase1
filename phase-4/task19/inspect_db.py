# inspect_db.py
from pathlib import Path
import duckdb

DB_PATH = Path(__file__).resolve().parents[2] / "pulseiq.duckdb"

con = duckdb.connect(str(DB_PATH), read_only=True)

print("TABLES AND VIEWS:")
for (name,) in con.execute(
    "SELECT table_name FROM information_schema.tables ORDER BY table_name"
).fetchall():
    print(" -", name)

print("\nCOLUMNS:")
for table, column, dtype in con.execute(
    "SELECT table_name, column_name, data_type FROM information_schema.columns "
    "ORDER BY table_name, ordinal_position"
).fetchall():
    print(f"  {table}.{column} ({dtype})")

con.close()