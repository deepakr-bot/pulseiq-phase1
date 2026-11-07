import json
import os
import sys

from budget_common import connect, table_cols, find, is_numeric, month_sql

args = sys.argv[1:]


def opt(name):
    return args[args.index(name) + 1] if name in args else None


os.makedirs("sql", exist_ok=True)
os.makedirs("reports", exist_ok=True)
con = connect(read_only=False)
bt = table_cols(con, "dw.budget_payroll_dept_month")

m_col = opt("--month-col") or find(bt, "month_start_date", "month_end_date", "month_end", "period_end_date",
                                   "month", "date_key", "period")
d_col = opt("--dept-col") or find(bt, "department_id", "dept_id", "department_name", "department", "dept")
cands = [c for c, t in bt.items() if is_numeric(t) and c not in (m_col, d_col)
         and not any(x in c.lower() for x in ("headcount", "_hc", "fte", "_id", "key", "year", "month", "quarter"))]
pref = [c for c in cands if "budget" in c.lower()] or cands
b_col = opt("--budget-col") or (pref[0] if pref else None)
hc_col = find({c: t for c, t in bt.items() if is_numeric(t)}, "headcount", "fte")

print("Columns chosen in budget_payroll_dept_month:")
print(f"  month      -> {m_col}")
print(f"  department -> {d_col}")
print(f"  budget     -> {b_col}   (other number columns: {[c for c in cands if c != b_col]})")
print(f"  headcount  -> {hc_col}")
if not (m_col and d_col and b_col):
    print("\nSTOP: could not find all three columns. Paste the output of check_budget_data.py here.")
    raise SystemExit(1)

vals = {str(v) for (v,) in con.execute(f'SELECT DISTINCT "{d_col}" FROM dw.budget_payroll_dept_month').fetchall()}
ids = {r[0] for r in con.execute("SELECT department_id FROM dw.dim_department").fetchall()}
names = {r[0] for r in con.execute("SELECT department_name FROM dw.dim_department").fetchall()}
by_id = len(vals & ids) >= len(vals & names)
print(f"  department values are {'department ids' if by_id else 'department names'}")

month_expr = month_sql(m_col, bt[m_col], "b")
dept_expr = f'CAST(b."{d_col}" AS VARCHAR)' if by_id else "d.department_id"
join = "" if by_id else f'LEFT JOIN dw.dim_department d ON CAST(b."{d_col}" AS VARCHAR) = d.department_name'
hc = f', SUM(b."{hc_col}") AS budget_headcount' if hc_col else ""

stmts = []
budget_sql = f"""CREATE OR REPLACE VIEW dw.v_budget_month AS
SELECT {month_expr} AS month, {dept_expr} AS department_id, SUM(b."{b_col}") AS budget{hc}
FROM dw.budget_payroll_dept_month b {join}
GROUP BY 1, 2"""
con.execute(budget_sql)
stmts.append(budget_sql)

print("\nBudget months found:", con.sql("SELECT MIN(month) a, MAX(month) z, COUNT(DISTINCT month) n FROM dw.v_budget_month").fetchone())
print("Payroll months found:", con.sql(
    "SELECT MIN(strftime(month_end,'%Y-%m')) a, MAX(strftime(month_end,'%Y-%m')) z, COUNT(DISTINCT month_end) n "
    "FROM dw.v_payroll_good").fetchone())

# ---- which actual measure does the budget describe? compare company totals on matching months ----
comp = con.sql("""
    WITH a AS (SELECT strftime(month_end, '%Y-%m') AS month, department_id,
                      SUM(gross_pay) g, SUM(net_pay) n, SUM(employer_cost) e
               FROM dw.v_payroll_good GROUP BY 1, 2)
    SELECT SUM(b.budget) AS budget, SUM(a.g) AS gross_pay, SUM(a.n) AS net_pay, SUM(a.e) AS employer_cost,
           COUNT(*) AS matched_dept_months
    FROM dw.v_budget_month b JOIN a ON a.month = b.month AND a.department_id = b.department_id""").df().iloc[0]
if comp["matched_dept_months"] == 0:
    print("\nSTOP: no department-month matches between budget and payroll. The month or department values differ.")
    print("Budget sample:", con.sql("SELECT month, department_id FROM dw.v_budget_month LIMIT 5").fetchall())
    print("Paste this output here.")
    raise SystemExit(1)

gaps = {k: abs(comp["budget"] - comp[k]) / comp["budget"] for k in ["gross_pay", "net_pay", "employer_cost"]}
measure = opt("--actual") or min(gaps, key=gaps.get)
print("\nWhich payroll measure is the budget closest to? (company totals on matching months)")
print(f"  budget {comp['budget']:,.0f}")
for k in gaps:
    print(f"  {k:14s} {comp[k]:,.0f}   gap {gaps[k]:.2%}")
print(f"  -> using {measure} as 'actual'  (override with --actual gross_pay | net_pay | employer_cost)")

stmts.append(f"""CREATE OR REPLACE VIEW dw.v_payroll_actual_month AS
SELECT strftime(month_end, '%Y-%m') AS month, department_id,
       SUM({measure}) AS actual, COUNT(DISTINCT employee_id) AS employees_paid
FROM dw.v_payroll_good
GROUP BY 1, 2""")
stmts.append("""CREATE OR REPLACE VIEW dw.v_payroll_variance AS
SELECT COALESCE(a.month, b.month) AS month,
       COALESCE(a.department_id, b.department_id) AS department_id,
       COALESCE(dep.department_name, COALESCE(a.department_id, b.department_id)) AS department,
       a.employees_paid, b.budget, a.actual,
       a.actual - b.budget AS variance,
       (a.actual - b.budget) * 100.0 / NULLIF(b.budget, 0) AS variance_pct,
       CASE WHEN a.actual > b.budget THEN 'Overspend'
            WHEN a.actual < b.budget THEN 'Underspend' ELSE 'On budget' END AS direction
FROM dw.v_budget_month b
FULL JOIN dw.v_payroll_actual_month a ON a.month = b.month AND a.department_id = b.department_id
LEFT JOIN dw.dim_department dep ON dep.department_id = COALESCE(a.department_id, b.department_id)""")
stmts.append("CREATE OR REPLACE VIEW main.v10_payroll_variance AS SELECT * FROM dw.v_payroll_variance")
for s in stmts[1:]:
    con.execute(s)

with open("sql/budget_views.sql", "w", encoding="utf-8") as f:
    f.write("-- Sign rule: variance = actual - budget. Positive = overspend. Negative = underspend.\n")
    f.write("-- Variance % = variance / budget * 100\n\n" + ";\n\n".join(stmts) + ";\n")
json.dump({"month_col": m_col, "dept_col": d_col, "budget_col": b_col, "headcount_col": hc_col,
           "dept_is_id": by_id, "actual_measure": measure,
           "sign_rule": "variance = actual - budget; positive = overspend"},
          open("budget_rules.json", "w"), indent=2)

print("\nROW CHECK")
print(con.sql("""SELECT COUNT(*) AS rows,
    SUM(CASE WHEN actual IS NOT NULL AND budget IS NOT NULL THEN 1 ELSE 0 END) AS matched,
    SUM(CASE WHEN actual IS NULL THEN 1 ELSE 0 END) AS budget_only,
    SUM(CASE WHEN budget IS NULL THEN 1 ELSE 0 END) AS actual_only
    FROM dw.v_payroll_variance""").df().to_string(index=False))
print("\nCompany variance by month (all departments, matched months only)")
print(con.sql("""SELECT month, ROUND(SUM(variance) * 100.0 / SUM(budget), 2) AS variance_pct
    FROM dw.v_payroll_variance WHERE actual IS NOT NULL AND budget IS NOT NULL GROUP BY 1 ORDER BY 1""").df().to_string(index=False))
print("\nSaved sql/budget_views.sql and budget_rules.json")
con.close()