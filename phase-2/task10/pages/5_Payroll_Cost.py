import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

MIN_GROUP = 5   # minimum group size (same rule as Task 4)

st.set_page_config(page_title="Payroll cost", layout="wide")
st.title("Payroll cost")


@st.cache_data
def q(sql):
    con = duckdb.connect("pulseiq.duckdb", read_only=True)
    try:
        return con.sql(sql).df()
    finally:
        con.close()


def inr(x):
    if x >= 1e7:
        return f"₹{x / 1e7:,.2f} Cr"
    if x >= 1e5:
        return f"₹{x / 1e5:,.2f} L"
    return f"₹{x:,.0f}"


try:
    dm = q("SELECT * FROM dw.v_payroll_dept_month ORDER BY month_end")
    size = q("SELECT * FROM dw.v_payroll_dept_size")
    ex = q("SELECT reason, COUNT(*) AS n_rows FROM dw.payroll_excluded GROUP BY reason ORDER BY 2 DESC")
except Exception:
    st.error("The payroll views do not exist yet. Close Streamlit, run `python create_payroll_views.py`, "
             "then start the app again.")
    st.stop()

dm["month_end"] = pd.to_datetime(dm["month_end"])
dm["month"] = dm["month_end"].dt.strftime("%Y-%m")

# ---------- Minimum group size rule ----------
big = sorted(size.loc[size["avg_employees"] >= MIN_GROUP, "department"])
n_small = len(size) - len(big)
dm = dm[dm["department"].isin(big)]
cells_hidden = int((dm["employees_paid"] < MIN_GROUP).sum())
dm = dm[dm["employees_paid"] >= MIN_GROUP]
n_excl = int(ex["n_rows"].sum()) if not ex.empty else 0

with st.expander("Rules used on this page", expanded=True):
    st.markdown(f"""
- **Gross pay** = total earnings before deductions (fixed pay, overtime and variable pay).
- **Net pay** = gross pay minus employee deductions (the amount paid out to employees).
- **Employer cost** = the `employer_cost` column of the payroll data, summed (total cost to the company for payroll), as in metric M09.
- **Cost per employee** = employer cost / number of employees paid, per month.
- **Bad rows:** {n_excl} payroll rows were excluded because they failed checks (see "Data quality" below).
- **Privacy:** only totals and averages are shown, never one person's pay. Departments with fewer than {MIN_GROUP} people
  ({n_small} department(s)) and department-months with fewer than {MIN_GROUP} people ({cells_hidden}) are hidden.
""")

# ---------- Sidebar ----------
months = sorted(dm["month"].unique())
m0, m1 = st.sidebar.select_slider("Months", options=months, value=(months[0], months[-1]))
chosen = st.sidebar.multiselect("Department", big, default=big)

sel = dm[dm["department"].isin(chosen) & dm["month"].between(m0, m1)]
if sel.empty:
    st.warning("Select at least one department.")
    st.stop()

# ---------- KPIs ----------
tot_g, tot_n, tot_e = sel["gross_pay"].sum(), sel["net_pay"].sum(), sel["employer_cost"].sum()
cpe = tot_e / sel["employees_paid"].sum()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Gross pay (total)", inr(tot_g))
k2.metric("Net pay (total)", inr(tot_n))
k3.metric("Employer cost (total)", inr(tot_e))
k4.metric("Avg monthly cost per employee", inr(cpe))

# ---------- Trend ----------
mo = (sel.groupby("month", as_index=False)
         .agg(gross=("gross_pay", "sum"), net=("net_pay", "sum"),
              employer=("employer_cost", "sum"), employees=("employees_paid", "sum")))
mo["cost_per_employee"] = mo["employer"] / mo["employees"]

st.header("Cost by month")
t = mo.melt(id_vars="month", value_vars=["gross", "net", "employer"], var_name="measure", value_name="amount")
t["measure"] = t["measure"].map({"gross": "Gross pay", "net": "Net pay", "employer": "Employer cost"})
fig = px.line(t, x="month", y="amount", color="measure", markers=True)
fig.update_yaxes(tickformat=",.0f", title="₹ per month")
st.plotly_chart(fig, use_container_width=True)

# ---------- By department ----------
st.header("Cost by department")
dd = (sel.groupby("department", as_index=False)
         .agg(gross=("gross_pay", "sum"), net=("net_pay", "sum"), employer=("employer_cost", "sum"),
              avg_employees=("employees_paid", "mean"), emp_months=("employees_paid", "sum")))
dd["cost_per_employee"] = dd["employer"] / dd["emp_months"]
dd = dd.sort_values("employer", ascending=False)

c1, c2 = st.columns(2)
c1.plotly_chart(px.bar(dd.sort_values("employer"), x="employer", y="department", orientation="h",
                       title="Employer cost by department (₹, selected months)",
                       labels={"employer": "₹"}), use_container_width=True)
tab = dd[["department", "avg_employees", "gross", "net", "employer", "cost_per_employee"]].copy()
tab.columns = ["department", "avg employees", "gross pay", "net pay", "employer cost", "cost per employee (month)"]
c2.dataframe(tab.round(0), hide_index=True, use_container_width=True)

# ---------- Cost per employee ----------
st.header("Cost per employee")
p1, p2 = st.columns(2)
f2 = px.line(mo, x="month", y="cost_per_employee", markers=True, title="Average monthly employer cost per employee")
f2.update_yaxes(tickformat=",.0f", title="₹ per employee")
p1.plotly_chart(f2, use_container_width=True)
p2.plotly_chart(px.bar(dd.sort_values("cost_per_employee"), x="cost_per_employee", y="department",
                       orientation="h", title="Cost per employee by department (₹ per month)",
                       labels={"cost_per_employee": "₹"}), use_container_width=True)

hm = (sel.assign(cpe=sel["employer_cost"] / sel["employees_paid"])
         .pivot(index="department", columns="month", values="cpe"))
st.subheader("Heatmap: employer cost per employee, department by month")
st.plotly_chart(px.imshow(hm, aspect="auto", color_continuous_scale="Blues", labels=dict(color="₹")),
                use_container_width=True)

# ---------- Data quality ----------
with st.expander("Data quality: rows excluded from this page", expanded=False):
    if ex.empty:
        st.write("No rows are excluded at the moment.")
    else:
        st.write(f"{n_excl} payroll rows were excluded. Reasons (counts only):")
        st.dataframe(ex, hide_index=True)
st.caption("No individual salary is shown: every number is a total or an average for a group of "
           f"at least {MIN_GROUP} people.")