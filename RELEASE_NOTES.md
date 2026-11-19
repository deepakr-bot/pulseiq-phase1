# Release notes

## [1.0.0] - 2026-11-18

Corrected after the tag was published. The v1.0.0 tag points to commit dfad8a8.

### Included
- Metrics API (FastAPI) live at https://pulseiq-metrics-api-mhmr.onrender.com/docs. Five metrics: active headcount, total active teams, total payroll expense, rolling 12-month attrition and on-time delivery rate.
- Each metric returns its value, definition, source table, lineage and last refresh time.
- Compliance endpoint `GET /audit/compliance-report`. Departments with average headcount below 5 are hidden (k = 5). The response reports the hidden count and the freshness fields.
- Lineage diagrams for each metric (`phase-4/task19/docs/lineage.md`) and API docs with screenshots (`phase-4/task19/docs/api.md`).
- Dashboard with 13 pages, live at https://pulseiq-dashboard.onrender.com. Page 13 is the self-service KPI explorer.
- Quality checks (`phase-4/task20/quality_checks.py`) and a 9-slide board deck (`phase-4/task20/build_board_deck.py`).
- Final challenge write-up (`phase-4/task20/final_challenge.md`).

### Not included
- Scheduled data refresh. Data changes only when the warehouse is rebuilt and redeployed.
- Automatic alerts when data is stale.
- Forecast pages or model output beyond what the warehouse already holds.
- Minimum group size rule on the five API metrics. It applies to the compliance endpoint and the payroll page.

### Known limits
- Data was last refreshed 2026-10-21 13:40:18 UTC, 27 days before this release. Values may be stale.
- Freshness is read from `etl_run_log.finished_at` by the helper functions.
- Quality checks: ETL freshness fails (27 days old). Headcount reconciliation fails: the metric view shows 440 and the fact table shows 441 for the latest month. Not yet investigated.
- Quarantined rows: 20 in `fact_task`, listed but not investigated.
- Lineage text is written by hand and summarises the ETL steps. It is not generated from pipeline code.
- Board deck recommendations are drafts and must be checked against the charts before presenting.
- The compliance endpoint is an internal control. It is not a formal compliance certification.
- Both services run on Render's free plan and sleep when idle. The first request can take up to 60 seconds.

### Changed
- Metric queries use schema-qualified names where needed (`dw.v_team_overall`).
- `active_headcount` corrected to 440 to match the metric view. Earlier documentation showed 460.
- Deployment status corrected: both services are live. The earlier notes said the API ran locally only.
- Freshness and lineage page claim removed. The dashboard has 13 pages.