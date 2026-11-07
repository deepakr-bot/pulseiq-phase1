# PulseIQ: Phase 2 (People and Teams)

Phase 2 covers tasks 6 to 10 of the PulseIQ data analytics course. It builds on the Phase 1 warehouse and analyses attendance, attrition, team delivery, payroll cost and budget. Each task has its own folder with its dashboard and its evidence.

## Tasks

| Task | Folder | What it shows |
|---|---|---|
| 6 | `task06/` | Attendance and leave trends by month and department, with holidays marked and three explained unusual months |
| 7 | `task07/` | Attrition analytics: exits by month, department and tenure, with predicted risk labelled "Predicted, not certain" |
| 8 | `task08/` | Team productivity: velocity, cycle time, on-time rate and blocked or reopened work, with a sprint selector |
| 9 | `task09/` | Payroll cost by department and month, reconciled to the answer key, with excluded rows listed and explained |
| 10 | `task10/` | Budget versus actual and KPI targets: variance, traffic lights, a written sign rule and recommendations |

## Data

Phase 2 uses the warehouse built in Phase 1 and the course dataset:
- `fact_attendance_monthly`, `fact_leave` and `dim_date` (task 6)
- `fact_headcount_monthly` and `fact_attrition_risk` (task 7)
- `fact_task`, `dim_team` and `dim_sprint` (task 8)
- `fact_payroll` and `dim_department`, checked against the reconciliation answer key (task 9)
- `budget_payroll_dept_month` and `kpi_targets` (task 10)

## How to run

Install the packages once:

pip install -r requirements.txt

Then run one task from the phase folder, for example:

streamlit run task09/app.py

Replace `task09` with the task you want to open.

## Checks and notes

- **Task 6:** attendance rates use working days as the denominator, and holidays are marked so that a dip is explained before it is reported.
- **Task 7:** predictions are labelled as predictions and are shown by group only, with a minimum group size applied so no individual can be identified.
- **Task 8:** the rules for velocity, cycle time, on-time rate and cancelled work are written on the page, and two teams are verified by hand.
- **Task 9:** payroll totals are reconciled to the answer key. Rows with bad data are excluded, and each exclusion is listed with its reason. Only totals and averages are shown.
- **Task 10:** variance is actual minus budget, so a positive number is an overspend. Traffic lights follow the rules in `kpi_targets`.

Each task's `reports` folder holds the screenshots, verification tables and written findings.