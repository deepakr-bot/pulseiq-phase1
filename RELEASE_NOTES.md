# Release notes

## [1.0.0] - 2026-11-18

### Included
- Metrics API (FastAPI) with five metrics: active headcount, total active teams,
  total payroll expense, rolling 12-month attrition, on-time delivery rate.
- Each endpoint returns value, definition, source table, lineage and last refresh.
- Lineage diagrams for all five metrics (docs/lineage.md).
- API documentation with examples and test screenshots (docs/api.md).
- Dashboard pages 1 to 13, plus a freshness and lineage page (task18).
- Quality and reconciliation checks (scripts/quality_checks.py) and a generated board deck
  (scripts/build_board_deck.py).

### Not included
- Deployment to a public host. The API runs locally at 127.0.0.1:8000.
- Automatic alerts when data is stale.
- Any forecast page or model output beyond what the warehouse already holds.

### Known limits
- The last ETL refresh is 2026-10-21, about four weeks before this release. Values may be stale.
- Freshness is taken from etl_run_log.finished_at. Confirm this matches the real load time.
- The payroll cost view may differ from the raw payroll fact table if rows are excluded.
  See payroll_excluded and the quality report.
- Lineage text is written by hand and summarises the ETL steps. It is not generated from pipeline code.
- The board deck recommendations are drafts and must be checked against the charts before presenting.

### Changed
- Metric queries now use schema-qualified names where needed (dw.v_team_overall).
- active_headcount corrected to 440 to match the metric view. Earlier documentation showed 460