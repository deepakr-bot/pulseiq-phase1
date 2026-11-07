# Task 15: Company health scorecard: KPI list

## KPIs

| KPI | Source view | Target | Why it belongs on the scorecard |
| --- | --- | --- | --- |
| Operating revenue (excl. interest) | m16_revenue | none in kpi_targets | Tracks the core top-line business growth and sales performance, excluding non-operational finance income. |
| Net profit | m18_operating_margin | none in kpi_targets | Provides the bottom-line financial health indicator, showing total earnings after all expenses and income items. |
| Operating margin | m18_operating_margin | none in kpi_targets | Measures overall profitability and operational efficiency by showing how effectively revenue turns into profit. |
| Payroll as % of revenue | m19_payroll_pct_of_revenue | none in kpi_targets | Monitors labor cost efficiency, ensuring workforce overhead stays aligned with revenue generation. |
| Days sales outstanding | m20_dso | none in kpi_targets | Evaluates cash flow management and collection efficiency from customers. |
| Attendance rate | m13_attendance_rate | 94.0 % (kpi_targets, department average) | Measures workforce reliability, operational availability, and staff presence at work. |
| Overtime share | m11_overtime_share | 1.5 % (kpi_targets, department average) | Indicates capacity constraints, workload pressure, and extra labor cost risks. |
| Monthly attrition | m04_attrition_rate_monthly | 1.0 % (kpi_targets, department average) | Tracks employee turnover, helping spot morale issues and retention risks early. |

## Notes

- **Revenue excludes interest income** (account 4900). The P&L page includes it, so its total for September 2026 is about 0.3 M higher: 80.3 M on the scorecard against 80.6 M on the P&L page.
- **Net profit and operating margin** come from `m18_operating_margin`, which includes interest income.
- **Company attendance, overtime and attrition** are simple averages of department values, not weighted by headcount.
- **Targets** exist only for attendance, overtime and attrition. Their company-level target is the average of the department targets for each month.
- **Status rule** (set for this scorecard, not taken from kpi_targets): green is on target, amber is within 10% of the target, red is further off.
- **Detail-page links** are live only when the scorecard runs in the Phase 3 app, which contains those pages. In this task folder they show as text, except where the page is present.
- **Print:** the scorecard is set to print on one A4 sheet. Print check: [write what you actually saw in print preview, or delete this line if you didn't check].

## Think for yourself

To streamline the scorecard to 5 KPIs, I would remove:

1. **Net profit:** Redundant alongside **Operating revenue** and **Operating margin**, which together communicate top-line size and overall profitability percentage without doubling up on financial metrics.
2. **Attendance rate:** Overlaps significantly with workforce capacity and engagement, whereas **Overtime share** and **Monthly attrition** serve as clearer warning indicators for operational strain and turnover risk.
3. **Overtime share:** Can be monitored directly within department-level reports; keeping **Payroll as % of revenue** already provides executive-level visibility into total labor cost efficiency.

**Final 5 selected KPIs:**

1. Operating revenue (excl. interest)
2. Operating margin
3. Payroll as % of revenue
4. Days sales outstanding
5. Monthly attrition