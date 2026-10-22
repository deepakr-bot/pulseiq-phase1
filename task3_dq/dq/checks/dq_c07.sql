SELECT invoice_id FROM dw.fact_invoice
WHERE amount_paid > total_amount + 0.01 OR balance_due < -0.01
