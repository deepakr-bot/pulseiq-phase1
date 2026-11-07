import os
import sys

import pandas as pd
from budget_common import connect, where_is

NAMES = ["budget_payroll_dept_month", "kpi_targets"]
src = sys.argv[1] if len(sys.argv) > 1 else None   # optional: a folder with CSV files or the xlsx workbook

con = connect(read_only=False)
con.execute("CREATE SCHEMA IF NOT EXISTS dw")

for name in NAMES:
    loc = where_is(con, name)
    if loc == "dw":
        print(f"{name}: already in dw")
    elif loc:
        con.execute(f"CREATE OR REPLACE TABLE dw.{name} AS SELECT * FROM {loc}.{name}")
        print(f"{name}: copied from {loc} into dw")
    else:
        done = False
        if src and os.path.isdir(src):
            for root, _, files in os.walk(src):
                for f in files:
                    if f.lower() == f"{name}.csv":
                        p = os.path.join(root, f).replace("\\", "/")
                        con.execute(f"CREATE OR REPLACE TABLE dw.{name} AS SELECT * FROM read_csv_auto('{p}')")
                        print(f"{name}: loaded from {p}")
                        done = True
        elif src and src.lower().endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(src, sheet_name=name)
                con.register("tmp_df", df)
                con.execute(f"CREATE OR REPLACE TABLE dw.{name} AS SELECT * FROM tmp_df")
                print(f"{name}: loaded from sheet '{name}' of {src}")
                done = True
            except Exception as e:
                print(f"{name}: could not read the workbook sheet ({str(e)[:70]})")
        if not done:
            print(f"{name}: NOT FOUND in the database. Run again with the path of your starter kit data folder, e.g.")
            print('   python load_budget_targets.py "C:\\path\\to\\03_Data"')

print()
for name in NAMES:
    try:
        print(f"dw.{name}: {con.sql(f'SELECT COUNT(*) FROM dw.{name}').fetchone()[0]} rows")
    except Exception:
        print(f"dw.{name}: missing")
con.close()