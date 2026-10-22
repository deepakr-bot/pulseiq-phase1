# Join map (from the README sheet)

| Fact table | Joins to | Keys used |
|---|---|---|
| fact_anomaly | dim_employee, dim_department, dim_date | employee_id (to employee_key), period_key |
| fact_attrition_risk | dim_employee, dim_department, dim_date | employee_key, department_id, as_of_date_key |
| fact_forecast | dim_department, dim_date | department_id, forecast_month_key |
| fact_task | dim_team, dim_sprint, dim_employee | team_id, sprint_id, assignee_employee_id (to employee_key) |
| fact_expense | dim_vendor, dim_account, dim_department, dim_date | vendor_id, category_account, department_id, expense_date_key |
| fact_invoice | dim_client, dim_account, dim_date | client_id, service_line_account, invoice_date_key |
| fact_invoice_payment | dim_date, fact_invoice | payment_date_key, invoice_id |
| fact_ledger | dim_account, dim_department, dim_date | account_code, cost_center_department_id, date_key |
| fact_headcount_monthly | dim_department, dim_date | department_id, date_key (month end) |
| fact_leave | dim_employee, dim_leave_type, dim_date | employee_key, leave_type_code, start_date_key, end_date_key |
| fact_attendance_monthly | dim_employee, dim_date, dim_department | employee_key, date_key (month end), department_id |
| fact_payroll | dim_employee, dim_date, dim_department, dim_role | employee_key (version valid at period end), date_key, department_id, role_id |