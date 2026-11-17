from pathlib import Path
import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

# Define dynamic paths relative to this script's location
BASE_DIR = Path(__file__).resolve().parent.parent
DB = str(BASE_DIR / "pulseiq.duckdb")
KEY_FILE = str(BASE_DIR / "reconciliation_answer_key.csv")

# DQ-04: June 2026 salary expense is 18,450 above the payroll run (known issue)
ADJ = {"2026-06": 18450.0}

@st.cache_data
def load():
    con = duckdb.connect(DB, read_only=True)
    acc = con.execute("SELECT * FROM dim_account").df()
    ven = con.execute("SELECT * FROM dim_vendor").df()
    gl = con.execute("SELECT * FROM fact_ledger").df()
    exp = con.execute("SELECT * FROM fact_expense").df()
    con.close()
    gl["entry_date"] = pd.to_datetime(gl["entry_date"])
    exp["expense_date"] = pd.to_datetime(exp["expense_date"])
    return acc, ven, gl, exp

acc, ven, gl, exp = load()
key = pd.read_csv(KEY_FILE)

st.title("Profit & Loss and Expense Analytics")
st.caption("Source: pulseiq.duckdb (tables loaded from PulseIQ_Dataset.xlsx). "
           "Zenith Nova Technologies, fictional. Amounts in INR.")

# Group accounts are headings: they never carry money
group_codes = acc.loc[acc.is_group == "Y", "account_code"]
group_rows = int(gl.account_code.isin(group_codes).sum())

# Detail P&L accounts only
pl_acc = acc[(acc.statement == "Profit & Loss") & (acc.is_group == "N")][
    ["account_code", "account_name", "account_type"]]
pl = gl.merge(pl_acc, on="account_code")
# Income = credit minus debit. Expense = debit minus credit. Both shown positive.
pl["amount"] = (pl.credit - pl.debit).where(pl.account_type == "INCOME",
                                            pl.debit - pl.credit)
pl["month"] = pl.entry_date.dt.to_period("M").dt.to_timestamp()

rev = pl[pl.account_type == "INCOME"]
cost = pl[pl.account_type == "EXPENSE"]

monthly = pd.DataFrame({
    "Revenue": rev.groupby("month").amount.sum(),
    "Expenses": cost.groupby("month").amount.sum(),
}).fillna(0)
monthly["Margin"] = monthly.Revenue - monthly.Expenses
monthly["Margin %"] = (monthly.Margin / monthly.Revenue * 100).round(1)
monthly.index.name = "month"

# Apply the DQ-04 adjustment to expenses, shown as its own column
monthly["DQ-04 adj"] = [ADJ.get(d.strftime("%Y-%m"), 0.0) for d in monthly.index]
monthly["Expenses"] = monthly["Expenses"] - monthly["DQ-04 adj"]
monthly["Margin"] = monthly.Revenue - monthly.Expenses
monthly["Margin %"] = (monthly.Margin / monthly.Revenue * 100).round(1)
m = monthly.reset_index()

# KPI row: full-period totals
total_rev = monthly["Revenue"].sum()
total_exp = monthly["Expenses"].sum()
total_profit = total_rev - total_exp
margin_pct = total_profit / total_rev * 100

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total revenue (INR)", f"{total_rev/1e6:,.1f} M")
k2.metric("Total expenses (INR)", f"{total_exp/1e6:,.1f} M")
k3.metric("Profit (INR)", f"{total_profit/1e6:,.1f} M")
k4.metric("Overall margin", f"{margin_pct:.1f} %")

st.subheader("Revenue, expenses and margin by month (INR)")
st.plotly_chart(px.line(m, x="month", y=["Revenue", "Expenses", "Margin"], markers=True))
st.plotly_chart(px.line(m, x="month", y="Margin %", markers=True, title="Margin %"))
st.dataframe(monthly.round(0))

st.subheader("P&L for one month")
options = monthly.index.strftime("%Y-%m").tolist()
choice = st.selectbox("Month", options, index=len(options) - 1)
mm = pl[pl.month == pd.Timestamp(choice + "-01")]
t = mm.groupby(["account_type", "account_name"]).amount.sum().reset_index()
r = t[t.account_type == "INCOME"][["account_name", "amount"]]
e = t[t.account_type == "EXPENSE"][["account_name", "amount"]]
tot_r, tot_e = r.amount.sum(), e.amount.sum()
adj = ADJ.get(choice, 0.0)
tot_e = tot_e - adj
table = pd.concat([
    r.rename(columns={"account_name": "Line"}),
    pd.DataFrame([{"Line": "Total Revenue", "amount": tot_r}]),
    e.rename(columns={"account_name": "Line"}),
    pd.DataFrame([{"Line": "DQ-04 adjustment", "amount": -adj}]),
    pd.DataFrame([{"Line": "Total Expenses", "amount": tot_e}]),
    pd.DataFrame([{"Line": "Margin", "amount": tot_r - tot_e}]),
], ignore_index=True).rename(columns={"amount": "Amount"})
st.dataframe(table.round(0), hide_index=True)

st.subheader("Expenses by category (full period)")
by_cat = cost.groupby("account_name").amount.sum().sort_values(ascending=False).reset_index()
st.plotly_chart(px.bar(by_cat, x="account_name", y="amount", title="Expense by category (INR)"))

st.subheader("Top 10 vendors (full period, excl. GST)")
v = exp.merge(ven[["vendor_id", "vendor_name"]], on="vendor_id")
top = (v.groupby("vendor_name").amount_excl_gst.sum()
       .nlargest(10).sort_values().reset_index())
st.plotly_chart(px.bar(top, x="amount_excl_gst", y="vendor_name", orientation="h",
                        title="Top 10 vendors (INR)"))

st.subheader("Tie-out checks")
bill_lines = pl[(pl.source_type == "EXPENSE") & (pl.account_type == "EXPENSE")].amount.sum()
checks = pd.DataFrame([
    ("Ledger balanced: total debits vs credits", gl.debit.sum(), gl.credit.sum()),
    ("Group accounts carry no postings", group_rows, 0),
    ("Expense bills vs ledger expense lines (excl. GST)", bill_lines, exp.amount_excl_gst.sum()),
    ("Revenue vs answer key", total_rev, key.ledger_revenue.sum()),
    ("Expenses vs answer key (after DQ-04 adjustment)", total_exp, key.ledger_total_expense.sum()),
    ("Profit vs answer key", total_profit, key.ledger_net_profit.sum()),
], columns=["Check", "Our figure", "Expected"])
checks["Difference"] = (checks["Our figure"] - checks["Expected"]).round(2)
checks["Status"] = checks["Difference"].abs().lt(1).map({True: "PASS", False: "FAIL"})
st.dataframe(checks.round(2), hide_index=True)