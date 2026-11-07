import os

import numpy as np
import pandas as pd
from budget_common import connect

pd.set_option("display.width", 220)
os.makedirs("reports", exist_ok=True)
con = connect()
v = con.sql("SELECT * FROM dw.v_kpi_status").df()
t = con.sql("SELECT * FROM dw.kpi_targets").df()
t["month"] = pd.to_datetime(t["month"]).dt.strftime("%Y-%m")


def monthly(sql, col):
    d = con.sql(sql).df()
    d["month"] = pd.to_datetime(d[col]).dt.strftime("%Y-%m")
    return d


att = monthly("SELECT department_id, month_end, attendance_rate AS v FROM main.m13_attendance_rate", "month_end")
ot = monthly("SELECT department_id, month_end, overtime_share_pct AS v FROM main.m11_overtime_share", "month_end")
ar = monthly("SELECT department_id, month, attrition_rate_pct AS v FROM main.m04_attrition_rate_monthly", "month")


def light(a, tg, higher, band):
    if pd.isna(a) or pd.isna(tg):
        return "Grey"
    if higher:
        return "Green" if a >= tg else ("Amber" if a >= tg - band else "Red")
    return "Green" if a <= tg else ("Amber" if a <= tg + band else "Red")


rows, cases = [], []
for kpi, src, tcol, higher, band in [("Attendance rate", att, "attendance_rate_target", True, 0.02),
                                     ("Overtime share", ot, "overtime_share_target_pct", False, 0.5),
                                     ("Monthly attrition", ar, "attrition_monthly_target_pct", False, 0.5)]:
    m = t.merge(src[["department_id", "month", "v"]], on=["department_id", "month"], how="left")
    m["by_hand"] = [light(a, g, higher, band) for a, g in zip(m["v"], m[tcol])]
    mv = v[v["kpi"] == kpi][["department_id", "month", "status", "actual", "target"]]
    j = m.merge(mv, on=["department_id", "month"], how="outer")
    bad = int((j["by_hand"] != j["status"]).sum())
    rows.append({"KPI": kpi, "department-months": len(j), "status differs from by-hand": bad,
                 "match": "YES" if bad == 0 else "NO"})
    for s in ["Red", "Amber", "Green"]:
        x = j[(j["status"] == s)].head(1)
        for _, r in x.iterrows():
            cases.append({"KPI": kpi, "department_id": r["department_id"], "month": r["month"],
                          "actual": round(r["actual"], 4), "target": r["target"], "status in view": r["status"],
                          "by hand": r["by_hand"]})

if "Task completion" in set(v["kpi"]):
    rows.append({"KPI": "Task completion", "department-months": int((v["kpi"] == "Task completion").sum()),
                 "status differs from by-hand": "not rechecked here", "match": "check 2 cases by hand"})

res = pd.DataFrame(rows)
cs = pd.DataFrame(cases)
print(res.to_string(index=False))
print("\nCases you can check with a calculator (one red, one amber, one green per KPI):")
print(cs.to_string(index=False))
res.to_csv("reports/kpi_verification_table.csv", index=False)
with open("reports/kpi_verification_table.md", "w", encoding="utf-8") as f:
    f.write("| " + " | ".join(res.columns) + " |\n|" + "---|" * len(res.columns) + "\n")
    for _, r in res.iterrows():
        f.write("| " + " | ".join(str(x) for x in r.values) + " |\n")
    f.write("\n| " + " | ".join(cs.columns) + " |\n|" + "---|" * len(cs.columns) + "\n")
    for _, r in cs.iterrows():
        f.write("| " + " | ".join(str(x) for x in r.values) + " |\n")
print("\nSaved reports/kpi_verification_table.md")
con.close()