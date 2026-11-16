# Task 16: Monthly report builder

Builds a one-page PDF report for any month in the data.

## Setup

1. Install Python 3.12 or newer.
2. From the repo root, create and activate a virtual environment:

python -m venv .venv
.venv\Scripts\activate

3. Install the pinned packages:

pip install -r phase-4/task16/requirements.txt


## Run

python phase-4/task16/build_report.py --month 2026-09


The PDF is written to `phase-4/task16/output/`. The report shows the month covered, the data cut-off (latest ledger date), five KPIs, a 12-month trend and the top expense categories.

## Data

The report reads `phase-3/pulseiq.duckdb`. Use `--db` to point at another copy.

## Scheduling

`.github/workflows/monthly-report.yml` runs the report on the first day of each month and uploads the PDF as a workflow artifact. It can also be run by hand from the Actions tab, with a month entered.

## Notes for new departments

The report totals across all departments, so a new department flows in when it appears in the fact tables. The metric views must be rebuilt first, or the new department will be missing from the KPIs.