SELECT expense_id FROM dw.fact_expense
WHERE ABS(total_amount - (amount_excl_gst + gst_amount)) > 0.01
