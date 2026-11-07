import json
import os
import sys

import numpy as np
import pandas as pd
from budget_common import connect

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
os.makedirs("reports", exist_ok=True)
cfg = json.load(open("budget_rules.json", encoding="utf-8"))
con = connect()

view = con.sql("""SELECT v.* FROM dw.v_payroll_variance v
                  JOIN dw.v_payroll_dept_size s ON s.department_id = v.department_id
                  WHERE v.actual IS NOT NULL AND v.budget IS NOT NULL
                    AND s.avg_employees >= 5 AND v.employees_paid >= 5""").df()

args = [a for a in sys.argv[1:] if "|" in a]
if args:
    picks = [tuple(a.split("|", 1)) for a in args[:3]]
else:
    s = view.sort_values("variance_pct").reset_index(drop=True)
    mid = (view["variance_pct"] - view["variance_pct"].median()).abs().idxmin()
    rows = [s.iloc[-1], s.iloc[0], view.loc[mid]]
    picks = [(r["department"], r["month"]) for r in rows]
print("Department-months checked:", picks)

# ---- raw data, read again with pandas (a different code path from the SQL views) ----
bud = con.sql("SELECT * FROM dw.budget_payroll_dept_month").df()
dep = con.sql("SELECT department_id, department_name FROM dw.dim_department").df()
pay = con.sql("""SELECT payroll_item_id, employee_id, department_id, period_end_date,
                        gross_pay, net_pay, employer_cost FROM dw.fact_payroll""").df()
excl = set(con.sql("SELECT payroll_item_id FROM dw.payroll_excluded").df()["payroll_item_id"])
pay = pay[~pay["payroll_item_id"].isin(excl)]
pay["month"] = pd.to_datetime(pay["period_end_date"]).dt.strftime("%Y-%m")


def norm_month(s):
    if np.issubdtype(s.dtype, np.datetime64):
        return s.dt.strftime("%Y-%m")
    if np.issubdtype(s.dtype, np.number):
        t = s.astype("Int64").astype(str)
        return t.where(t.str.len() < 8, pd.to_datetime(t, format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m")
                       ).where(t.str.len() >= 8, t.str[:4] + "-" + t.str[4:6])
    return s.astype(str).str[:7]


bud["month"] = norm_month(bud[cfg["month_col"]])
if cfg["dept_is_id"]:
    bud["department_id"] = bud[cfg["dept_col"]].astype(str)
else:
    bud = bud.merge(dep, left_on=cfg["dept_col"], right_on="department_name", how="left")
name_to_id = dict(zip(dep["department_name"], dep["department_id"]))

out = []
for dept, month in picks:
    did = name_to_id.get(dept, dept)
    b = bud[(bud["department_id"] == did) & (bud["month"] == month)][cfg["budget_col"]].sum()
    p = pay[(pay["department_id"] == did) & (pay["month"] == month)]
    a = p[cfg["actual_measure"]].sum()
    var = a - b
    pct = var / b * 100
    row = view[(view["department"] == dept) & (view["month"] == month)].iloc[0]
    ok = abs(var - row["variance"]) < 0.01 and abs(pct - row["variance_pct"]) < 0.001
    out.append({"department": dept, "month": month, "payroll rows": len(p), "budget": round(b, 2),
                "actual": round(a, 2), "variance (actual - budget)": round(var, 2),
                "variance %": round(pct, 3), "view variance": round(row["variance"], 2),
                "view variance %": round(row["variance_pct"], 3), "match": "YES" if ok else "NO"})

res = pd.DataFrame(out)
print(res.to_string(index=False))
res.to_csv("reports/verification_table.csv", index=False)
with open("reports/verification_table.md", "w", encoding="utf-8") as f:
    f.write("| " + " | ".join(res.columns) + " |\n|" + "---|" * len(res.columns) + "\n")
    for _, r in res.iterrows():
        f.write("| " + " | ".join(str(x) for x in r.values) + " |\n")
print("\nSaved reports/verification_table.md and reports/verification_table.csv")
print("All match:", (res["match"] == "YES").all())