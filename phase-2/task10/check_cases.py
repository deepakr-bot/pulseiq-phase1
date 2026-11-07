import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)
print(con.sql("""
    SELECT department,
           ROUND(SUM(variance), 0) AS post_freeze_variance_inr,
           COUNT(*) AS months
    FROM dw.v_payroll_variance
    WHERE department IN ('Data & AI', 'Product & Design')
      AND month >= '2025-07'
      AND actual IS NOT NULL AND budget IS NOT NULL
    GROUP BY department
""").df().to_string(index=False))