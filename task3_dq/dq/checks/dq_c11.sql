SELECT prediction_id FROM dw.fact_attrition_risk
WHERE as_of_date < (SELECT MAX(as_of_date) FROM dw.fact_attrition_risk) - 7
