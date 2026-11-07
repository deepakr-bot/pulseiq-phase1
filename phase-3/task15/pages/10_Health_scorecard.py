import os
import duckdb
import pandas as pd
import streamlit as st

DB = "pulseiq.duckdb"
FILE = "PulseIQ_Dataset.xlsx"

# Print setting: one A4 page, no sidebar or menu
st.markdown("""
<style>
@media print {
  header, footer, [data-testid="stSidebar"], [data-testid="stToolbar"] {display: none !important;}
  @page {size: A4; margin: 10mm;}
}
</style>
""", unsafe_allow_html=True)

def month_key(s):
    return pd.to_datetime(s).dt.to_period("M").dt.to_timestamp()

@st.cache_data
def load():
    con = duckdb.connect(DB, read_only=True)
    data = {
        "m04": con.execute("SELECT department_id, month, attrition_rate_pct FROM m04_attrition_rate_monthly").df(),
        "m11": con.execute("SELECT department_id, month_end AS month, overtime_share_pct FROM m11_overtime_share").df(),
        "m13": con.execute("SELECT department_id, month_end AS month, attendance_rate FROM m13_attendance_rate").df(),
        "m16": con.execute("SELECT month, SUM(revenue) AS revenue FROM m16_revenue GROUP BY month").df(),
        "m18": con.execute("SELECT month, net_profit, operating_margin_pct FROM m18_operating_margin").df(),
        "m19": con.execute("SELECT month, payroll_pct_of_revenue FROM m19_payroll_pct_of_revenue").df(),
        "m20": con.execute("SELECT month_end AS month, dso_days FROM m20_dso").df(),
    }
    con.close()
    data["kt"] = pd.read_excel(FILE, sheet_name="kpi_targets")
    return data

d = load()

def monthly(df, col):
    x = df.assign(month=month_key(df["month"]))
    return x.set_index("month")[col]

def company_mean(df, col):
    x = df.assign(month=month_key(df["month"]))
    return x.groupby("month")[col].mean()

# Company-level targets = average of department targets for each month
kt = d["kt"].assign(month=month_key(d["kt"]["month"]))
targets = kt.groupby("month")[["attendance_rate_target", "overtime_share_target_pct",
                               "attrition_monthly_target_pct"]].mean()

table = pd.concat({
    "Revenue (INR)": monthly(d["m16"], "revenue"),
    "Net profit (INR)": monthly(d["m18"], "net_profit"),
    "Operating margin (%)": monthly(d["m18"], "operating_margin_pct"),
    "Payroll as % of revenue": monthly(d["m19"], "payroll_pct_of_revenue"),
    "DSO (days)": monthly(d["m20"], "dso_days"),
    "Attendance rate": company_mean(d["m13"], "attendance_rate"),
    "Overtime share (%)": company_mean(d["m11"], "overtime_share_pct"),
    "Monthly attrition (%)": company_mean(d["m04"], "attrition_rate_pct"),
}, axis=1, sort=True).sort_index()
table["Attendance target"] = targets["attendance_rate_target"]
table["Overtime target (%)"] = targets["overtime_share_target_pct"]
table["Attrition target (%)"] = targets["attrition_monthly_target_pct"]

# label, column, unit, higher is better, target column, detail page, source view
CARDS = [
    ("Operating revenue (excl. interest)", "Revenue (INR)", "INR", True, None, "pages/7_Profit_and_Loss.py", "m16_revenue"),
    ("Net profit", "Net profit (INR)", "INR", True, None, "pages/7_Profit_and_Loss.py", "m18_operating_margin"),
    ("Operating margin", "Operating margin (%)", "%", True, None, "pages/7_Profit_and_Loss.py", "m18_operating_margin"),
    ("Payroll as % of revenue", "Payroll as % of revenue", "%", False, None, "pages/5_Payroll_Cost.py", "m19_payroll_pct_of_revenue"),
    ("Days sales outstanding", "DSO (days)", "days", False, None, "pages/8_Receivables_and_Cash.py", "m20_dso"),
    ("Attendance rate", "Attendance rate", "ratio", True, "Attendance target", "pages/2_Attendance_and_Leave.py", "m13_attendance_rate"),
    ("Overtime share", "Overtime share (%)", "%", False, "Overtime target (%)", "pages/5_Payroll_Cost.py", "m11_overtime_share"),
    ("Monthly attrition", "Monthly attrition (%)", "%", False, "Attrition target (%)", "pages/3_Attrition.py", "m04_attrition_rate_monthly"),
]

def fmt(v, unit):
    if pd.isna(v):
        return "n/a"
    if unit == "INR":
        return f"{v / 1e6:,.1f} M"
    if unit == "%":
        return f"{v:,.1f} %"
    if unit == "ratio":
        return f"{v * 100:,.1f} %"
    if unit == "days":
        return f"{v:,.1f} days"
    return f"{v:,.2f}"

def status(v, t, higher):
    if pd.isna(v) or pd.isna(t):
        return "⚪ No target"
    if higher:
        if v >= t:
            return "🟢 On target"
        return "🟡 Near target" if v >= t * 0.9 else "🔴 Off target"
    if v <= t:
        return "🟢 On target"
    return "🟡 Near target" if v <= t * 1.1 else "🔴 Off target"

# Page
st.title("Company health scorecard")
st.caption("Each number comes from a metric view in pulseiq.duckdb. Targets come from kpi_targets. "
           "Status rule: green = on target, amber = within 10% of target, red = further off.")

months = table.dropna(subset=["Revenue (INR)"]).index
labels = [m.strftime("%b %Y") for m in months]
choice = st.selectbox("Month", labels, index=len(labels) - 1)
i = labels.index(choice)
cur = table.loc[months[i]]
prev = table.loc[months[i - 1]] if i > 0 else None

cols = st.columns(4)
for k, (label, col, unit, higher, tcol, page, source) in enumerate(CARDS):
    v = cur[col]
    t = cur[tcol] if tcol else None
    delta = None
    if prev is not None and not pd.isna(prev[col]) and not pd.isna(v):
        delta = f"{v - prev[col]:+,.2f} vs last month"
    with cols[k % 4]:
        with st.container(border=True):
            st.markdown(f"**{label}**")
            st.metric("Value", fmt(v, unit), delta=delta,
                      delta_color="normal" if higher else "inverse")
            st.write(f"Target: {fmt(t, unit) if tcol else 'none in kpi_targets'}")
            st.write(f"Status: {status(v, t, higher)}")
            st.caption(f"Source: {source}")
            if os.path.exists(page):
                st.page_link(page, label="Open detail page")
            else:
                st.caption(f"Detail page: {page}")

st.subheader("Where each number comes from")
defs = pd.DataFrame([
    (c[0], c[6], "kpi_targets (average of departments)" if c[4] else "none", c[5])
    for c in CARDS
], columns=["KPI", "Metric view", "Target source", "Detail page"])
st.dataframe(defs, hide_index=True)
st.caption("Company figures for attendance, overtime and attrition are simple averages of "
           "departments, not weighted by headcount.")