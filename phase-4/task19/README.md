# Task 19: Analytics API and Data Lineage

A small read-only FastAPI service that returns five PulseIQ metrics. Each response includes the value, its definition, source table, lineage from raw feed to dashboard, and when the data was last refreshed.

Status: runs locally only. Not yet deployed.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service name and link to docs |
| GET | `/health` | Service check |
| GET | `/metrics` | List all metrics with freshness statement |
| GET | `/metrics/{metric_id}` | One metric: value, definition, source, lineage, refresh time |

Interactive docs: `http://127.0.0.1:8000/docs`

## Metrics

| metric_id | Name | Source |
|---|---|---|
| `active_headcount` | Active Headcount | `m01_headcount` (from `fact_headcount_monthly`) |
| `total_teams` | Total Active Teams | `v_team_overall` (from `fact_task`) |
| `total_payroll_expense` | Total Payroll Expense (Employer Cost) | `v_payroll_company_month` (from `fact_payroll`) |
| `attrition_12m` | Company Attrition (Rolling 12 Months) | `v5_company_attrition_12m` (from `fact_headcount_monthly`) |
| `on_time_delivery_rate` | On-Time Delivery Rate | `v_team_overall` (from `fact_task`) |

Lineage diagrams for each metric are in `docs/lineage.md`. Endpoint examples and sample responses are in `docs/api.md`.

## Files

- `main.py`: the API. Metric definitions and SQL queries are in the `METRICS` dictionary.
- `inspect_db.py`: lists the tables and columns in the warehouse. Use it to find names for new queries.
- `docs/lineage.md`: lineage diagrams (Mermaid).
- `docs/api.md`: endpoint docs, curl examples and screenshots.
- `docs/screenshots/`: test screenshots from `/docs`.

The API reads `pulseiq.duckdb` from the repo root. Do not keep a second copy inside this folder.

## Requirements

From the repo root:

```bash
pip install -r requirements.txt
```

## How to run

From the repo root, with the virtual environment active:

```bash
cd phase-4\task19
uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000/docs` and run:

- `GET /metrics`
- `GET /metrics/active_headcount`

Or from a terminal:

```bash
curl http://127.0.0.1:8000/metrics/active_headcount
```

## Current values

Data last refreshed: 2026-10-21 13:40:18 UTC.

| metric_id | Value |
|---|---|
| active_headcount | 440 |
| total_teams | 16 |
| total_payroll_expense | 55519621.87 |
| attrition_12m | 13.88 |
| on_time_delivery_rate | 92.9 |

## Known limits

- Runs locally only. Deployment is required by the project overview and is not yet done.
- Headcount has not been checked against `reconciliation_answer_key.csv`. The quality check shows a one-person gap (view 440, fact table 441).
- The minimum group size rule is not yet applied to these metrics.
- Freshness is taken from `etl_run_log.finished_at`. The data is about four weeks old.
- Lineage text is written by hand and summarises the ETL steps.