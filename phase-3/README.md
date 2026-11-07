markdown
# PulseIQ: Phase 3 (Finance and Cash)

Phase 3 covers tasks 11 to 15 of the PulseIQ data analytics course. Each task is a Streamlit dashboard in its own folder, with the screenshots and written evidence for that task in a `reports` folder.

## Tasks

| Task | Folder | What it shows |
|---|---|---|
| 11 | `task11/` | Profit and loss: revenue, expenses, margin, expense categories and top vendors, tied to the answer key |
| 12 | `task12/` | Receivables, ageing and cash: open invoices, days to pay, overdue balances and bank cash |
| 13 | `task13/` | Cross-department impact: headcount, payroll, overtime and attendance combined by department and month |
| 14 | `task14/` | AI signals: anomalies ranked by money at risk, and a forecast with an 80% range |
| 15 | `task15/` | Company health scorecard: eight headline KPIs with values, targets and status |

## Data

The shared data files sit in the root folder, and every task reads from them.

- `PulseIQ_Dataset.xlsx`: the course dataset
- `pulseiq.duckdb`: the warehouse with all loaded tables, including the metric views used in task 15
- `reconciliation_answer_key.csv`: the answer key used to check tasks 11 and 12
- `reference_summary_dept_month.csv`: the reference table used to check task 13

## How to run

Install the packages once:

pip install -r requirements.txt


Then run one task from the root folder:

streamlit run task11/app.py


Replace `task11` with `task12`, `task13`, `task14` or `task15` to open another task.

## Results and checks

Each task's `reports` folder holds the screenshots and written findings. The tie-out tables in tasks 11, 12 and 13 show each check as PASS or FAIL, with the expected figure beside it.

- **Task 11** ties revenue, expenses and profit to the answer key. One known difference, 18,450 of salary expense in June 2026, is applied as a labelled adjustment.
- **Task 12** ties open receivables and the monthly receivables balance to the answer key, and the bank closing balance.
- **Task 13** matches the reference table on eight measures for 198 department-months, after excluding eight rows with non-standard IDs.
- **Task 14** labels every AI output as AI-generated and shows the limits of the forecast. No past forecast has an actual value yet, so forecast error is not calculated.
- **Task 15** uses the metric views in `pulseiq.duckdb`. Only attendance, overtime and attrition have targets, and their company-level targets are averages of the department targets.

## Notes

- Revenue on the task 15 scorecard excludes interest income (account 4900), so it is about 0.3 M lower than the P&L total for September 2026.
- Detail-page links on the task 15 scorecard show as text in this repo, because the other task pages are not part of it.
- The data is the course dataset, a fictional company. The checks confirm consistency with the answer key, not agreement with real company records.

## Author

Deepak R