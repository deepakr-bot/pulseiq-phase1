WITH p AS (SELECT strftime(CAST(period_end_date AS DATE), '%Y-%m') AS month, SUM(employer_cost) AS cost
           FROM dw.fact_payroll GROUP BY 1),
l AS (SELECT strftime(CAST(entry_date AS DATE), '%Y-%m') AS month, SUM(debit - credit) AS exp
      FROM dw.fact_ledger
      WHERE CAST(account_code AS VARCHAR) IN ('5001','5002','5003','5004','5005') GROUP BY 1)
SELECT p.month, p.cost, l.exp, p.cost - l.exp AS diff
FROM p JOIN l USING (month) WHERE ABS(p.cost - l.exp) > 0.01
