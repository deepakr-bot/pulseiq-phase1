import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\nRow counts")
for t in ["raw.fact_payroll", "clean.fact_payroll", "dw.fact_payroll", "main.dw_fact_payroll"]:
    try:
        print(f"  {t}: {con.sql(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
    except Exception:
        print(f"  {t}: not found")

print("\nPeriod and departments in dw.fact_payroll")
print(con.sql("""SELECT MIN(period_end_date) AS first_period, MAX(period_end_date) AS last_period,
    COUNT(DISTINCT LAST_DAY(period_end_date)) AS months,
    COUNT(DISTINCT department_id) AS departments,
    COUNT(DISTINCT payroll_item_id) AS distinct_item_ids, COUNT(*) AS n_rows
    FROM dw.fact_payroll""").df().to_string(index=False))

print("\nheadcount_flag values")
print(con.sql("SELECT headcount_flag, COUNT(*) AS n FROM dw.fact_payroll GROUP BY 1 ORDER BY 1").df().to_string(index=False))

print("\nCompany totals as-is (all rows)")
print(con.sql("""SELECT ROUND(SUM(gross_pay),2) AS gross, ROUND(SUM(net_pay),2) AS net,
    ROUND(SUM(employer_cost),2) AS employer_cost FROM dw.fact_payroll""").df().to_string(index=False))

print("\nQuarantine reasons for fact_payroll (counts only)")
try:
    print(con.sql("""SELECT reason, COUNT(*) AS n FROM main.quarantine
                     WHERE table_name = 'fact_payroll' GROUP BY 1 ORDER BY 2 DESC""").df().to_string(index=False))
except Exception as e:
    print("  no quarantine table:", str(e)[:60])

print("\nHow your Task 4 metric views were defined")
v = con.sql("""SELECT view_name, sql FROM duckdb_views()
               WHERE view_name IN ('m07_gross_pay','m08_net_pay','m09_payroll_cost','m10_cost_per_head')
               ORDER BY view_name""").df()
for _, r in v.iterrows():
    print("\n--", r["view_name"])
    print(r["sql"])
con.close()