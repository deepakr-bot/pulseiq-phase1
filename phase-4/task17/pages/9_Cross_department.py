from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Cross-department impact", layout="wide")

BASE_DIR = Path(__file__).resolve().parent.parent
FILE = BASE_DIR / "PulseIQ_Dataset.xlsx"
REF_FILE = BASE_DIR / "reference_summary_dept_month.csv"

PERIOD_START, PERIOD_END = pd.Timestamp("2025-04-01"), pd.Timestamp("2026-09-01")
MEASURES = ["employer_cost", "overtime_pay", "overtime_hours", "headcount_end", "exits",
            "hires", "employees_paid", "late_arrivals", "attrition_rate_monthly_pct"]

@st.cache_data
def load():
    s = pd.read_excel(FILE, sheet_name=["fact_headcount_monthly", "fact_attendance_monthly",
                                         "fact_payroll", "dim_department"])
    return (s["fact_headcount_monthly"], s["fact_attendance_monthly"],
            s["fact_payroll"], s["dim_department"])

hc, att, pay, dept = load()

st.title("Cross-department impact view")
st.caption("Grain: one row per department and month. Source: PulseIQ_Dataset.xlsx. Amounts in INR.")

# Exclude rows with non-standard IDs (known planted issues)
pay_bad = pay[~pay.payroll_item_id.str.match(r"^PI-\d{6}$")]
att_bad = att[~att.attendance_fact_id.str.match(r"^FA-\d{5}$")]
pay = pay.drop(pay_bad.index)
att = att.drop(att_bad.index)

st.subheader("Rows excluded (non-standard IDs)")
st.write(f"Payroll rows excluded: {len(pay_bad)}, employer cost {pay_bad.employer_cost.sum():,.2f}. "
         f"Attendance rows excluded: {len(att_bad)}.")
st.dataframe(pay_bad[["payroll_item_id", "employee_id", "department_id", "period_end_date",
                      "employer_cost"]], hide_index=True)
st.dataframe(att_bad[["attendance_fact_id", "employee_id", "department_id", "period_end_date",
                      "late_arrivals"]], hide_index=True)

# 1. Each source at the same grain: department x month
hc["month"] = pd.to_datetime(hc.month_start_date).dt.to_period("M").dt.to_timestamp()
hc_m = hc.groupby(["department_id", "month"]).agg(
    headcount_start=("headcount_start", "sum"),
    headcount_end=("headcount_end", "sum"),
    exits=("exits", "sum"),
    hires=("hires", "sum"),
    attrition_rate_monthly_pct=("attrition_rate_monthly_pct", "sum"),
).reset_index()

pay["month"] = pd.to_datetime(pay.period_end_date).dt.to_period("M").dt.to_timestamp()
pay_m = pay.groupby(["department_id", "month"]).agg(
    employer_cost=("employer_cost", "sum"),
    overtime_pay=("overtime_pay", "sum"),
    employees_paid=("employee_id", "nunique"),
).reset_index()

att["month"] = pd.to_datetime(att.period_end_date).dt.to_period("M").dt.to_timestamp()
att["leave_days"] = att.paid_leave_days + att.unpaid_absence_days
att_m = att.groupby(["department_id", "month"]).agg(
    overtime_hours=("overtime_hours", "sum"),
    late_arrivals=("late_arrivals", "sum"),
    leave_days=("leave_days", "sum"),
    employee_months=("employee_id", "nunique"),
).reset_index()

# 2. Join one at a time (outer, so no department-month is dropped)
combined_all = (hc_m.merge(pay_m, on=["department_id", "month"], how="outer")
                    .merge(att_m, on=["department_id", "month"], how="outer")
                    .merge(dept[["department_id", "department_name"]], on="department_id", how="left"))

st.subheader("Join check: totals before and after the join")
checks = pd.DataFrame([
    ("Employer cost", pay.employer_cost.sum(), combined_all.employer_cost.sum()),
    ("Overtime hours", att.overtime_hours.sum(), combined_all.overtime_hours.sum()),
    ("Exits", hc.exits.sum(), combined_all.exits.sum()),
], columns=["Check", "Source total", "Joined total"])
checks["Difference"] = (checks["Source total"] - checks["Joined total"]).round(2)
checks["Status"] = checks["Difference"].abs().lt(1).map({True: "PASS", False: "FAIL"})
st.dataframe(checks.round(2), hide_index=True)

combined = combined_all[(combined_all.month >= PERIOD_START) & (combined_all.month <= PERIOD_END)].copy()
combined["attrition_pct"] = combined.exits / combined.headcount_start * 100
combined["overtime_hours_per_head"] = combined.overtime_hours / combined.employee_months

# 3. Compare with the reference file
st.subheader("Comparison with reference (department x month, Apr 2025 to Sep 2026)")
if not REF_FILE.exists():
    st.warning(f"{REF_FILE.name} not found in {BASE_DIR}.")
else:
    ref = pd.read_csv(REF_FILE)
    ref["month"] = pd.to_datetime(ref.month).dt.to_period("M").dt.to_timestamp()
    cmp_ = ref[["department_id", "month"] + MEASURES].merge(
        combined[["department_id", "month"] + MEASURES],
        on=["department_id", "month"], suffixes=("_ref", "_ours"))
    st.write(f"Department-months compared: {len(cmp_)}")

    summary, detail = [], []
    for c in MEASURES:
        d = (cmp_[c + "_ours"] - cmp_[c + "_ref"]).round(2)
        summary.append((c, int((d.abs() > 0.5).sum()), round(d.sum(), 2)))
        bad = cmp_.loc[d.abs() > 0.5, ["department_id", "month"]].copy()
        if len(bad):
            bad["measure"] = c
            bad["ours"] = cmp_.loc[bad.index, c + "_ours"]
            bad["reference"] = cmp_.loc[bad.index, c + "_ref"]
            bad["difference"] = d.loc[bad.index]
            detail.append(bad)

    st.dataframe(pd.DataFrame(summary, columns=["Measure", "Rows that differ",
                                                "Total difference (ours - reference)"]),
                 hide_index=True)
    if detail:
        st.write("Rows that still differ:")
        st.dataframe(pd.concat(detail).round(2), hide_index=True)
    else:
        st.success("Every measure matches the reference for every department and month.")

# 4. Department comparison
st.subheader("Department comparison (full period)")
by_dept = combined.groupby("department_name").agg(
    employer_cost=("employer_cost", "sum"),
    overtime_pay=("overtime_pay", "sum"),
    exits=("exits", "sum"),
    headcount_start=("headcount_start", "sum"),
    overtime_hours=("overtime_hours", "sum"),
    employee_months=("employee_months", "sum"),
).reset_index()
by_dept["attrition_pct"] = by_dept.exits / by_dept.headcount_start * 100
by_dept["overtime_hours_per_head"] = by_dept.overtime_hours / by_dept.employee_months
by_dept = by_dept.round(2)
st.dataframe(by_dept, hide_index=True)

st.plotly_chart(px.scatter(
    by_dept, x="overtime_hours_per_head", y="attrition_pct",
    size="employer_cost", text="department_name",
    title="Overtime hours per head vs monthly attrition %, bubble size = employer cost"))