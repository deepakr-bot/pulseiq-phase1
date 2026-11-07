import duckdb
import pandas as pd

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
con = duckdb.connect("pulseiq.duckdb", read_only=True)

BASE = """FROM dw.v_payroll_variance v JOIN dw.v_payroll_dept_size s ON s.department_id = v.department_id
          WHERE v.actual IS NOT NULL AND v.budget IS NOT NULL AND s.avg_employees >= 5 AND v.employees_paid >= 5"""

print("\n1) Total (departments with 5 or more people, matched months)")
print(con.sql(f"""SELECT COUNT(DISTINCT v.month) AS n_months, ROUND(SUM(v.budget)) AS budget_total,
   ROUND(SUM(v.actual)) AS actual_total, ROUND(SUM(v.variance)) AS variance_total,
   ROUND(SUM(v.variance) * 100.0 / SUM(v.budget), 2) AS variance_pct {BASE}""").df().to_string(index=False))

rk = con.sql(f"""SELECT v.department AS department, ROUND(SUM(v.budget)) AS budget_total,
   ROUND(SUM(v.actual)) AS actual_total, ROUND(SUM(v.variance)) AS variance_total,
   ROUND(SUM(v.variance) * 100.0 / SUM(v.budget), 2) AS variance_pct,
   SUM(CASE WHEN v.variance > 0 THEN 1 ELSE 0 END) AS months_over, COUNT(*) AS n_months,
   ROUND(AVG(v.employees_paid), 1) AS avg_employees {BASE}
   GROUP BY 1 ORDER BY SUM(v.variance) DESC""").df()
rk.insert(0, "rank", range(1, len(rk) + 1))
print("\n2) Ranking by overspend (Rs)")
print(rk.to_string(index=False))

print("\n3) Ranking by variance %")
print(rk.sort_values("variance_pct", ascending=False)
        [["department", "variance_pct", "variance_total", "months_over", "n_months"]].to_string(index=False))

print("\n4) Company variance % by month")
mo = con.sql(f"""SELECT v.month AS month, ROUND(SUM(v.variance) * 100.0 / SUM(v.budget), 2) AS variance_pct,
   ROUND(SUM(v.variance)) AS variance_total {BASE} GROUP BY 1 ORDER BY 1""").df()
print(mo.to_string(index=False))
half = len(mo) // 2
print(f"\n   first {half} months average variance %: {mo['variance_pct'][:half].mean():.2f}"
      f" | last {len(mo) - half} months: {mo['variance_pct'][half:].mean():.2f}")

for dep in rk["department"].head(2):
    print(f"\n5) Top overspend department: {dep} (by month)")
    print(con.sql(f"""SELECT v.month AS month, ROUND(v.variance) AS variance_total,
        ROUND(v.variance_pct, 2) AS variance_pct, v.employees_paid AS people_paid {BASE}
        AND v.department = '{dep}' ORDER BY v.month""").df().to_string(index=False))

print("\n6) People paid, first versus last month (the budget has no headcount column)")
for dep in rk["department"].head(2):
    p = con.sql(f"""SELECT v.month AS month, v.employees_paid AS people_paid {BASE}
        AND v.department = '{dep}' ORDER BY v.month""").df()
    print(f"  {dep}: {p['month'].iloc[0]} = {p['people_paid'].iloc[0]} people, "
          f"{p['month'].iloc[-1]} = {p['people_paid'].iloc[-1]} people")
con.close()