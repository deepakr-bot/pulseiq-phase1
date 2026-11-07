## fact_task

| column | type | can be empty? | allowed values / rule |
|---|---|---|---|
| task_id | string | no | unique TASK-nnnnn |
| team_id | string | no | exists in dim_team |
| sprint_id | string | no | exists in dim_sprint |
| assignee_employee_id | string | no | exists in dim_employee |
| task_type | string | no | Feature | Bug | Chore | Spike |
| priority | string | no | P1..P4 |
| story_points | int | no | 1,2,3,5,8,13 |
| created_date | date | no | <= started_date |
| started_date | date | yes | blank only when To Do |
| due_date | date | no | sprint end date |
| completed_date | date | yes | required when status = Done; >= started_date |
| status | string | no | Done | In Progress | Blocked | To Do | Cancelled |
| reopened_count | int | no | >= 0 |

## fact_anomaly

| column | type | can be empty? | allowed values / rule |
|---|---|---|---|
| result_id | string | no | unique, format AN-nnnn |
| source_dataset | string | no | attendance_monthly_features | payroll_monthly_features |
| record_id | string | no | exists in source dataset |
| employee_id | string | no | exists in dim_employee |
| period | date | no | month end or start date |
| anomaly_score | decimal(4,3) | no | 0 to 1, higher is more unusual |
| flagged | char(1) | no | Y or N |
| reason_code | string | no | one of the published codes |
| reason_text | string | no | plain English |
| money_at_risk | decimal(14,2) | yes | blank for attendance rows |
| model_version | string | no | semantic version text |
| scored_at | timestamp | no | UTC |

## fact_attrition_risk

| column | type | can be empty? | allowed values / rule |
|---|---|---|---|
| prediction_id | string | no | unique AR-nnnn |
| employee_id | string | no | exists in dim_employee and active |
| department_id | string | no | exists in dim_department |
| as_of_date | date | no | same for the whole batch |
| risk_score_12m | decimal(4,3) | no | 0 to 1 |
| risk_band | string | no | Low | Medium | High |
| top_reason_1..3 | string | yes | plain English |
| model_version | string | no | text |

