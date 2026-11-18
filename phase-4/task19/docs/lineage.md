# Data Lineage: PulseIQ Metrics API

Freshness: all five metrics currently report a last refresh of 2026-10-21 13:40:18 UTC.

## 1. Active Headcount (`active_headcount`)

```mermaid
flowchart LR
  A[HR Raw Feed] --> B[ETL Pipeline]
  B --> C[(fact_headcount_monthly)]
  C --> D[m01_headcount]
  D --> E[Metrics API /metrics/active_headcount]
  E --> F[Executive Dashboard]
```

Breaks if: `employee_id`, `month` or `headcount` changes in the HR feed.

## 2. Total Active Teams (`total_teams`)

```mermaid
flowchart LR
  A[Task Tracker Raw Feed] --> B[ETL Pipeline]
  B --> C[(fact_task)]
  C --> D[v_team_overall]
  D --> E[Metrics API /metrics/total_teams]
  E --> F[Executive Dashboard]
```

Breaks if: `team_id` changes in the task feed.

## 3. Total Payroll Expense (`total_payroll_expense`)

```mermaid
flowchart LR
  A[Payroll Raw Feed] --> B[ETL Pipeline]
  B --> C[(fact_payroll)]
  C --> D[v_payroll_company_month]
  D --> E[Metrics API /metrics/total_payroll_expense]
  E --> F[Executive Dashboard]
```

Breaks if: `employer_cost`, `month_end` or `employee_id` changes in the payroll feed.

## 4. Company Attrition, Rolling 12 Months (`attrition_12m`)

```mermaid
flowchart LR
  A[HR Raw Feed] --> B[ETL Pipeline]
  B --> C[(fact_headcount_monthly)]
  C --> D[v5_company_attrition_12m]
  D --> E[Metrics API /metrics/attrition_12m]
  E --> F[Executive Dashboard]
```

Breaks if: `exits`, `headcount_end` or `month` changes in the HR feed.

## 5. On-Time Delivery Rate (`on_time_delivery_rate`)

```mermaid
flowchart LR
  A[Task Tracker Raw Feed] --> B[ETL Pipeline]
  B --> C[(fact_task)]
  C --> D[v_team_overall]
  D --> E[Metrics API /metrics/on_time_delivery_rate]
  E --> F[Executive Dashboard]
```

Breaks if: `due_date`, `completed_date` or `on_time` logic changes in the task feed.

## Change-impact summary

| Raw feed changes | Metrics affected |
|---|---|
| HR feed (employee, headcount, exits) | active_headcount, attrition_12m |
| Task tracker feed (team, due date, completion) | total_teams, on_time_delivery_rate |
| Payroll feed (employer cost, month) | total_payroll_expense |