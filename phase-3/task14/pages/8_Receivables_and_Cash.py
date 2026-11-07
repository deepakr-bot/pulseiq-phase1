import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

DB = "pulseiq.duckdb"
KEY_FILE = "reconciliation_answer_key.csv"
CUTOFF = pd.Timestamp("2026-09-30")
OPEN = ["SENT", "OVERDUE", "PARTIALLY_PAID"]
BANK_ACCOUNT = 1001

@st.cache_data
def load():
    con = duckdb.connect(DB, read_only=True)
    inv = con.execute("SELECT * FROM fact_invoice").df()
    pay = con.execute("SELECT * FROM fact_invoice_payment").df()
    cli = con.execute("SELECT client_id, client_name, payment_terms_days FROM dim_client").df()
    bank = con.execute(f"""
        SELECT entry_date, debit, credit FROM fact_ledger
        WHERE account_code = {BANK_ACCOUNT}
    """).df()
    con.close()
    inv["invoice_date"] = pd.to_datetime(inv["invoice_date"])
    inv["due_date"] = pd.to_datetime(inv["due_date"])
    pay["payment_date"] = pd.to_datetime(pay["payment_date"])
    bank["entry_date"] = pd.to_datetime(bank["entry_date"])
    key = pd.read_csv(KEY_FILE, parse_dates=["month"]).set_index("month")
    return inv, pay, cli, bank, key

inv, pay, cli, bank, key = load()

st.title("Receivables, ageing and cash")
st.caption("Source: pulseiq.duckdb. Cutoff 30 Sep 2026. Amounts in INR.")
st.markdown("**Open invoices** are those with status SENT, OVERDUE or PARTIALLY_PAID. "
            "PAID, CANCELLED and DRAFT invoices are closed and excluded.")

# Open invoices, with days past due at the cutoff
op = inv[inv.status.isin(OPEN) & (inv.balance_due > 0)].merge(cli, on="client_id", how="left").copy()
op["days_past_due"] = (CUTOFF - op.due_date).dt.days

def bucket(d):
    if d <= 0:
        return "Not yet due"
    if d <= 30:
        return "1-30 days past due"
    if d <= 60:
        return "31-60 days past due"
    if d <= 90:
        return "61-90 days past due"
    return "90+ days past due"

op["bucket"] = op.days_past_due.apply(bucket)
order = ["Not yet due", "1-30 days past due", "31-60 days past due",
         "61-90 days past due", "90+ days past due"]
ageing = op.groupby("bucket").balance_due.sum().reindex(order, fill_value=0).reset_index()
total_open = op.balance_due.sum()

st.subheader("Receivables ageing")
c1, c2 = st.columns(2)
c1.metric("Total open receivables (INR)", f"{total_open:,.0f}")
c2.metric("Open invoices", f"{len(op)}")
st.plotly_chart(px.bar(ageing, x="bucket", y="balance_due", title="Open balance by ageing bucket"))
st.dataframe(ageing, hide_index=True)

# Monthly receivables against the answer key
def closing_ar(end):
    billed = inv[(inv.invoice_date <= end) & ~inv.status.isin(["CANCELLED", "DRAFT"])].total_amount.sum()
    paid = pay[pay.payment_date <= end].amount.sum()
    return billed - paid

ar_rows = []
for m in key.index:
    end = m + pd.offsets.MonthEnd(0)
    ar_rows.append((m.strftime("%Y-%m"), closing_ar(end), key.loc[m, "receivables_closing_balance"]))
ar = pd.DataFrame(ar_rows, columns=["Month", "Our receivables", "Answer key"])
ar["Difference"] = (ar["Our receivables"] - ar["Answer key"]).round(2)

st.subheader("Month-end receivables vs answer key")
st.plotly_chart(px.line(ar, x="Month", y=["Our receivables", "Answer key"], markers=True,
                        title="Closing receivables by month (INR)"))
st.dataframe(ar.round(0), hide_index=True)

st.subheader("Average days to pay by client (paid invoices)")
paid = inv[inv.status == "PAID"].merge(cli, on="client_id", how="left")
dtp = (paid.groupby(["client_name", "payment_terms_days"]).days_to_pay
       .agg(["mean", "count"]).reset_index())
dtp["gap"] = dtp["mean"] - dtp["payment_terms_days"]
dtp = dtp.sort_values("mean", ascending=False).round(1)
dtp.columns = ["Client", "Terms (days)", "Avg days to pay", "Paid invoices", "Gap vs terms"]
st.dataframe(dtp, hide_index=True)

st.subheader("Clients with the most overdue money")
overdue = (op[op.days_past_due > 0].groupby("client_name").balance_due.sum()
           .sort_values(ascending=False).head(10).reset_index())
st.plotly_chart(px.bar(overdue, x="balance_due", y="client_name", orientation="h",
                       title="Overdue balance by client (INR)"))

st.subheader("Cash in and cash out by month")
bank["month"] = bank.entry_date.dt.to_period("M").dt.to_timestamp()
cash = bank.groupby("month").agg(cash_in=("debit", "sum"), cash_out=("credit", "sum")).reset_index()
client_rec = (pay.assign(month=pay.payment_date.dt.to_period("M").dt.to_timestamp())
              .groupby("month").amount.sum().reset_index(name="client_receipts"))
cash = cash.merge(client_rec, on="month", how="left").fillna(0)
st.plotly_chart(px.bar(cash, x="month", y=["cash_in", "cash_out"], barmode="group",
                       title="Bank cash in and cash out (INR)"))
st.plotly_chart(px.line(cash, x="month", y=["cash_in", "client_receipts"], markers=True,
                        title="Bank receipts vs client payments (INR)"))

st.subheader("Tie-out checks")
bank_closing = (bank.debit - bank.credit).sum()
sep_key = key.iloc[-1]
checks = pd.DataFrame([
    ("Bucket sum = total open receivables", ageing.balance_due.sum(), total_open),
    ("Open receivables Sep 2026 vs answer key", total_open, sep_key["receivables_closing_balance"]),
    ("Monthly receivables vs answer key (max abs difference)",
     ar["Difference"].abs().max(), 0),
    ("Bank closing balance Sep 2026 vs answer key", bank_closing, sep_key["bank_closing_balance"]),
], columns=["Check", "Our figure", "Expected"])
checks["Difference"] = (checks["Our figure"] - checks["Expected"]).round(2)
checks["Status"] = checks["Difference"].abs().lt(1).map({True: "PASS", False: "FAIL"})
st.dataframe(checks.round(2), hide_index=True)