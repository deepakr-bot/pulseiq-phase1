SELECT MAX(finished_at) AS last_load FROM main.etl_run_log
HAVING MAX(finished_at) IS NULL
    OR MAX(finished_at) < CAST(now() AS TIMESTAMP) - INTERVAL 24 HOUR
