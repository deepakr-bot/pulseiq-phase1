SELECT entry_id FROM dw.fact_ledger GROUP BY entry_id
HAVING ABS(SUM(debit) - SUM(credit)) > 0.005
