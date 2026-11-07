import glob
import os
import sys

import duckdb
import pandas as pd

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
TOL = 0.01
SAVE = "--save" in sys.argv
os.makedirs("reports", exist_ok=True)

files = sorted(glob.glob("reference/*.csv"))
files = [f for f in files if "PQ-09" in f] or files
if not files:
    print("No answer key CSV found in the reference folder.")
    raise SystemExit(1)
key = pd.read_csv(files[0])
key["_month"] = pd.to_datetime(key["month"]).dt.strftime("%Y-%m")
key = key[["_month", "employees_paid", "payroll_gross_pay", "payroll_net_pay", "payroll_employer_cost"]]

con = duckdb.connect("pulseiq.duckdb", read_only=not SAVE)
MON = "strftime(LAST_DAY(p.period_end_date), '%Y-%m')"


def month_totals(where="TRUE"):
    return con.sql(f"""SELECT {MON} AS _month, COUNT(*) AS rows_, COUNT(DISTINCT p.employee_id) AS emp,
        SUM(p.gross_pay) AS gross, SUM(p.net_pay) AS net, SUM(p.employer_cost) AS employer
        FROM dw.fact_payroll p WHERE {where} GROUP BY 1""").df()


def compare(mine):
    m = mine.merge(key, on="_month", how="outer").sort_values("_month").reset_index(drop=True)
    m["d_gross"] = (m["gross"].fillna(0) - m["payroll_gross_pay"].fillna(0)).round(2)
    m["d_net"] = (m["net"].fillna(0) - m["payroll_net_pay"].fillna(0)).round(2)
    m["d_emp"] = (m["employer"].fillna(0) - m["payroll_employer_cost"].fillna(0)).round(2)
    m["d_count"] = m["emp"].fillna(0) - m["employees_paid"].fillna(0)
    m["differs"] = (m[["d_gross", "d_net", "d_emp"]].abs().max(axis=1) > TOL) | (m["d_count"] != 0)
    return m


print("Answer key file:", files[0])
m = compare(month_totals())
show = m[["_month", "rows_", "emp", "employees_paid", "differs"]].copy()
show["differs"] = show["differs"].map({True: "YES", False: "no"})
show.columns = ["month", "my rows", "my distinct employees", "key employees_paid", "totals differ?"]
print("\n1) Month by month (no amounts shown)")
print(show.to_string(index=False))

picks = []
print("\n2) Looking for the row behind each difference")
for _, r in m[m["differs"]].iterrows():
    month = r["_month"]
    if max(abs(r["d_gross"]), abs(r["d_net"]), abs(r["d_emp"])) <= TOL:
        print(f"  {month}: only the employee count differs; paste this output so I can adapt the script.")
        continue
    cand = con.sql(f"""
        SELECT p.payroll_item_id, p.run_id, p.department_id,
          (SELECT COUNT(*) FROM dw.fact_payroll q WHERE q.employee_id = p.employee_id
             AND strftime(LAST_DAY(q.period_end_date), '%Y-%m') = '{month}') AS rows_for_employee,
          CASE WHEN e.employee_id IS NULL THEN 1 ELSE 0 END AS not_in_master,
          CASE WHEN e.hire_date IS NOT NULL AND e.hire_date > LAST_DAY(p.period_end_date) THEN 1 ELSE 0 END AS hired_after,
          CASE WHEN e.exit_date IS NOT NULL AND e.exit_date < DATE_TRUNC('month', p.period_end_date) THEN 1 ELSE 0 END AS exited_before,
          CASE WHEN regexp_matches(p.payroll_item_id, '^PI-[0-9]+$') THEN 0 ELSE 1 END AS odd_id
        FROM dw.fact_payroll p
        LEFT JOIN (SELECT employee_id, MIN(hire_date) AS hire_date, MAX(exit_date) AS exit_date
                   FROM dw.dim_employee GROUP BY 1) e ON p.employee_id = e.employee_id
        WHERE {MON} = '{month}'
          AND ABS(p.gross_pay - ({r['d_gross']})) < {TOL}
          AND ABS(p.net_pay - ({r['d_net']})) < {TOL}
          AND ABS(p.employer_cost - ({r['d_emp']})) < {TOL}
        ORDER BY p.payroll_item_id""").df()
    if cand.empty:
        print(f"  {month}: no single row matches the difference (a changed amount, not an extra row?).")
        continue

    print(f"\n  {month}: {len(cand)} candidate row(s) (evidence only, no employee IDs, no amounts)")
    print(cand.to_string(index=False))

    dupc = cand[cand["rows_for_employee"] >= 2]
    chosen = None
    if len(dupc) >= 2:
        chosen = dupc.sort_values(["odd_id", "payroll_item_id"]).iloc[1:]
    elif len(dupc) == 1:
        chosen = dupc
    else:
        strong = cand[(cand["not_in_master"] == 1) | (cand["hired_after"] == 1) | (cand["exited_before"] == 1)]
        if len(strong) == 1:
            chosen = strong
        elif len(cand) == 1:
            chosen = cand
        else:
            odd = cand[cand["odd_id"] == 1]
            if len(odd) == 1:
                chosen = odd
    if chosen is None or chosen.empty:
        print(f"  -> {month}: cannot choose safely between these rows. Paste this output here.")
        continue

    for _, c in chosen.iterrows():
        parts = []
        if c["rows_for_employee"] >= 2:
            parts.append("second payroll row for the same employee in the month")
        if c["exited_before"] == 1:
            parts.append("employee had already left before this month")
        if c["hired_after"] == 1:
            parts.append("employee had not joined yet")
        if c["not_in_master"] == 1:
            parts.append("employee is not in the employee master")
        if c["odd_id"] == 1:
            parts.append("payroll_item_id does not follow the normal pattern")
        reason = "; ".join(parts) if parts else "extra row"
        reason += " (and the answer key has no such row)"
        picks.append({"payroll_item_id": c["payroll_item_id"], "month": month, "run_id": c["run_id"],
                      "department_id": c["department_id"], "reason": reason})
    print(f"  -> {month}: chose {len(chosen)} row(s)")

if not picks:
    print("\nNo rows selected. Paste this output here and I will adapt the script.")
    con.close()
    raise SystemExit(0)

pk = pd.DataFrame(picks)
print("\n3) Rows to exclude (IDs and reasons only)")
print(pk.to_string(index=False))

ids = ", ".join("'" + i + "'" for i in pk["payroll_item_id"])
after = compare(month_totals(f"p.payroll_item_id NOT IN ({ids})"))
n_diff = int(after["differs"].sum())
print(f"\n4) After excluding these {len(pk)} rows: months that still differ = {n_diff} of {len(after)}")
reconciles = n_diff == 0
print("RECONCILES WITH THE ANSWER KEY:", "YES" if reconciles else "NO")

print("\n5) Rows whose payroll_item_id does not follow the usual pattern (supporting evidence only)")
print(con.sql(f"""SELECT p.payroll_item_id, {MON} AS month, p.department_id
    FROM dw.fact_payroll p WHERE NOT regexp_matches(p.payroll_item_id, '^PI-[0-9]+$')
    ORDER BY 1""").df().to_string(index=False))

if SAVE:
    if not reconciles:
        print("\nNot saving, because some months still differ.")
    else:
        con.execute("CREATE TABLE IF NOT EXISTS dw.payroll_excluded (payroll_item_id VARCHAR, reason VARCHAR)")
        con.execute("DELETE FROM dw.payroll_excluded")
        con.register("ex", pk[["payroll_item_id", "reason"]])
        con.execute("INSERT INTO dw.payroll_excluded SELECT payroll_item_id, reason FROM ex")
        names = dict(con.sql("SELECT department_id, department_name FROM dw.dim_department").fetchall())
        pk["department"] = pk["department_id"].map(names).fillna(pk["department_id"])
        pk[["payroll_item_id", "month", "run_id", "department_id", "department", "reason"]].to_csv(
            "reports/excluded_rows.csv", index=False)
        with open("reports/excluded_rows_table.md", "w", encoding="utf-8") as f:
            f.write("| payroll_item_id | month | department | reason |\n|---|---|---|---|\n")
            for _, x in pk.iterrows():
                f.write(f"| {x['payroll_item_id']} | {x['month']} | {x['department']} | {x['reason']} |\n")
        print("\nSaved to dw.payroll_excluded, reports/excluded_rows.csv and reports/excluded_rows_table.md")
else:
    print("\nNothing saved. If this looks right, close Streamlit and run:  python find_bad_rows_from_key.py --save")
con.close()