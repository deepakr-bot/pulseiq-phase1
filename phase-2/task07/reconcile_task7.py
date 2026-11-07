import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\nA) Exits Jan 2024 to Sep 2026: page view vs metric view m03")
print(con.sql("""SELECT
  (SELECT SUM(exits) FROM dw.v_exits_monthly WHERE month BETWEEN '2024-01-01' AND '2026-09-01') AS page_exits,
  (SELECT SUM(exits) FROM main.m03_exits     WHERE month BETWEEN '2024-01-01' AND '2026-09-01') AS m03_exits""").df())

print("\nB) 12-month attrition to Sep 2026: page logic vs v5_company_attrition_12m")
print(con.sql("""SELECT ROUND(SUM(exits)*100.0/(SUM(avg_headcount)/12),2) AS page_12m_pct
  FROM dw.v_exits_monthly WHERE month BETWEEN '2025-10-01' AND '2026-09-01'""").df())
print(con.sql("SELECT * FROM main.v5_company_attrition_12m ORDER BY month DESC LIMIT 3").df())

print("\nC) Voluntary 12-month rate, Operations & IT (D09), Sep 2026")
print(con.sql("""SELECT ROUND(SUM(voluntary_exits)*100.0/(SUM(avg_headcount)/12),2) AS page_vol_pct
  FROM dw.v_exits_monthly
  WHERE department='Operations & IT' AND month BETWEEN '2025-10-01' AND '2026-09-01'""").df())
print(con.sql("""SELECT * FROM main.m06_voluntary_attrition_rate
  WHERE department_id='D09' ORDER BY month DESC LIMIT 2""").df())