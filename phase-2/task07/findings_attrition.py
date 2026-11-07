import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\n1) Exits and attrition by year")
print(con.sql("""SELECT YEAR(month) yr, COUNT(DISTINCT month) months, SUM(exits) exits,
  SUM(voluntary_exits) voluntary,
  ROUND(SUM(voluntary_exits)*100.0/NULLIF(SUM(exits),0),1) vol_pct,
  ROUND(SUM(exits)*12*100.0/SUM(avg_headcount),1) annual_pct
  FROM dw.v_exits_monthly GROUP BY 1 ORDER BY 1""").df().to_string())

print("\n2) Departments, last 12 months (avg headcount >= 5)")
print(con.sql("""WITH x AS (SELECT department, SUM(exits) ex, SUM(avg_headcount) hc
  FROM dw.v_exits_monthly
  WHERE month > (SELECT MAX(month) FROM dw.v_exits_monthly) - INTERVAL 12 MONTH
  GROUP BY 1)
  SELECT department, ex, ROUND(hc/12,1) avg_hc, ROUND(ex*100.0/(hc/12),1) pct
  FROM x WHERE hc/12 >= 5 ORDER BY pct DESC""").df().to_string())

print("\n3) Tenure at exit")
print(con.sql("""SELECT COUNT(*) leavers, ROUND(MEDIAN(tenure_years),1) median_yrs,
  ROUND(AVG(CASE WHEN tenure_years<2 THEN 1.0 ELSE 0 END)*100,1) pct_under_2yrs
  FROM dw.v_exit_tenure""").df())

print("\n4) Predicted risk (departments with >= 5 scored)")
print(con.sql("""SELECT department, scored, ROUND(high*100.0/scored,1) high_pct
  FROM dw.v_risk_by_dept WHERE scored >= 5 ORDER BY high_pct DESC""").df().to_string())

print("\n5) Top predicted drivers in the High band")
print(con.sql("""SELECT reason, mentions FROM dw.v_risk_reasons
  WHERE UPPER(risk_band)='HIGH' ORDER BY mentions DESC LIMIT 5""").df())