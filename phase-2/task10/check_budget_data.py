import duckdb
import pandas as pd
from budget_common import connect, where_is

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 60)
con = connect()

for name in ["budget_payroll_dept_month", "kpi_targets"]:
    schemas = [s for s in ("dw", "clean", "raw", "main") if con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?", [s, name]).fetchone()[0]]
    print(f"\n===== {name}: found in schemas {schemas or 'NONE'}")
    loc = where_is(con, name)
    if not loc:
        continue
    t = f"{loc}.{name}"
    print("rows:", con.sql(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
    print(con.sql(f"DESCRIBE {t}").df()[["column_name", "column_type"]].to_string(index=False))
    print("\nfirst 5 rows:")
    print(con.sql(f"SELECT * FROM {t} LIMIT 5").df().to_string())
    df = con.sql(f"SELECT * FROM {t}").df()
    print("\ncolumns with few different values (value: how many rows):")
    for c in df.columns:
        n = df[c].nunique(dropna=True)
        if df[c].dtype == object and n <= 15:
            print(f"  {c}: {df[c].value_counts(dropna=False).to_dict()}")
        elif n <= 3:
            print(f"  {c}: {df[c].value_counts(dropna=False).to_dict()}")

print("\n===== Payroll side (from Task 9)")
print(con.sql("""SELECT MIN(month_end) first_month, MAX(month_end) last_month,
                 COUNT(DISTINCT department_id) departments FROM dw.v_payroll_good""").df().to_string(index=False))
con.close()