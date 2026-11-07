SELECT task_id FROM dw.fact_task
WHERE completed_date < started_date
   OR (status = 'Done' AND completed_date IS NULL)
