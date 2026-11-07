import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)

for v in ["m03_exits", "m04_attrition_rate_monthly", "m06_voluntary_attrition_rate",
          "v5_company_attrition_12m", "v5_department"]:
    print("\n==", v)
    print(con.sql(f"SELECT * FROM main.{v} LIMIT 4").df().to_string())

print("\nExit types (employment_status) among leavers")
print(con.sql("""SELECT employment_status, COUNT(*) n FROM dw.dim_employee
                 WHERE is_current='Y' AND exit_date IS NOT NULL GROUP BY 1 ORDER BY 2 DESC""").df())

print("\nRisk bands (latest as-of)")
print(con.sql("""SELECT as_of_date, risk_band, COUNT(*) n FROM dw.fact_attrition_risk
                 GROUP BY 1,2 ORDER BY 1,2""").df())

print("\nHeadcount table range and totals")
print(con.sql("""SELECT MIN(month_start_date) first_month, MAX(month_start_date) last_month,
                 SUM(exits) exits, SUM(voluntary_exits) voluntary FROM dw.fact_headcount_monthly""").df())

print("\nDepartments")
print(con.sql("SELECT department_id, department_name FROM dw.dim_department ORDER BY 1").df().to_string())