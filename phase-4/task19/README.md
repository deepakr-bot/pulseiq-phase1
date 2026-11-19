# Task 19: Analytics API and Data Lineage

A read-only FastAPI service that returns five PulseIQ metrics. Each response includes the value, its definition, the source table, the lineage from raw feed to dashboard, and when the data was last refreshed. It also includes a compliance endpoint that applies a k-anonymity rule to department headcounts.

**Live API:** https://pulseiq-metrics-api-mhmr.onrender.com/docs

Example value: https://pulseiq-metrics-api-mhmr.onrender.com/metrics/active_headcount

The free Render plan sleeps when idle. The first visit can take up to 60 seconds.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service name and link to docs |
| GET | `/health` | Service check |
| GET | `/metrics` | List all metrics with freshness statement |
| GET | `/metrics/{metric_id}` | One metric: value, definition, source, lineage, refresh time |
| GET | `/audit/compliance-report` | Department headcounts with k-anonymity rule (k = 5) applied |

Interactive docs: https://pulseiq-metrics-api-mhmr.onrender.com/docs

## Metrics

| metric_id | Name | Source |
|---|---|---|
| `active_headcount` | Active Headcount | `m01_headcount` (from `fact_headcount_monthly`) |
| `total_teams` | Total Active Teams | `v_team_overall` (from `fact_task`) |
| `total_payroll_expense` | Total Payroll Expense (Employer Cost) | `v_payroll_company_month` (from `fact_payroll`) |
| `attrition_12m` | Company Attrition (Rolling 12 Months) | `v5_company_attrition_12m` (from `fact_headcount_monthly`) |
| `on_time_delivery_rate` | On-Time Delivery Rate | `v_team_overall` (from `fact_task`) |

Lineage diagrams for each metric are in `docs/lineage.md`. Endpoint examples and sample responses are in `docs/api.md`.

## Current values

Data last refreshed: 2026-10-21 13:40:18 UTC. Values are from this refresh.

| metric_id | Value |
|---|---|
| active_headcount | 440 |
| total_teams | 16 |
| total_payroll_expense | 55,519,621.87 |
| attrition_12m | 13.88 |
| on_time_delivery_rate | 92.9 |

## Compliance endpoint

`GET /audit/compliance-report` reads `dw.v_payroll_dept_size` and returns departments whose average headcount is at least 5. Departments below 5 are hidden and counted in `hidden_departments_count`. The response includes the freshness fields from the ETL log.

Limits: this applies only to department-level group sizes, not to month-level or multi-filter views. It is an internal control, not a formal certification.

## Files

- `main.py`: the API. Metric definitions and SQL queries are in the `METRICS` dictionary. The compliance endpoint is `get_compliance_report()`.
- `inspect_db.py`: lists the tables and columns in the warehouse.
- `docs/lineage.md`: lineage diagrams (Mermaid).
- `docs/api.md`: endpoint docs, curl examples and screenshots.
- `docs/screenshots/`: test screenshots.

The API reads `pulseiq.duckdb` from the repo root. Do not keep a second copy inside this folder.

## Run locally

From the repo root, with the virtual environment active:

```bash
pip install -r requirements.txt
cd phase-4\task19
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs.

## Known limits

- Data is from 21 October 2026, 27 days before the checks. Values may be stale.
- Headcount view shows 440; the fact table shows 441 for the latest month. Not yet investigated.
- Scheduled refresh is not running.
- Minimum group size is applied to the compliance endpoint only, not to the five metrics.
- Lineage text is written by hand and summarises the ETL steps.
- Hosted on Render's free plan, so it sleeps when idle.