import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

LABEL = "AI-generated, for human review"

@st.cache_data
def load():
    x = pd.read_excel("PulseIQ_Dataset.xlsx", sheet_name=["fact_anomaly", "fact_forecast"])
    con = duckdb.connect("pulseiq.duckdb", read_only=True)
    bt = con.execute("SELECT * FROM m28_forecast_error_mape").df()
    con.close()
    an = x["fact_anomaly"]
    an["period"] = pd.to_datetime(an["period"])
    fc = x["fact_forecast"]
    fc["forecast_month"] = pd.to_datetime(fc["forecast_month"])
    bt["month"] = pd.to_datetime(bt["month"])
    return an, fc, bt

an, fc, bt = load()

st.title("AI signals")
st.warning(LABEL)
st.caption("Source: PulseIQ_Dataset.xlsx and pulseiq.duckdb. Amounts in INR.")

# 1. Anomalies by type, ranked by money at risk
st.subheader("1. Anomalies by type, ranked by money at risk")
st.write("Plain note: money at risk is only available for payroll anomalies. "
         "Attendance anomalies are counted but have no money value. " + LABEL + ".")
by_type = an.groupby("reason_code").agg(
    anomalies=("result_id", "count"),
    with_money_value=("money_at_risk", "count"),
    money_at_risk=("money_at_risk", "sum"),
).reset_index().sort_values("money_at_risk", ascending=False)
st.plotly_chart(px.bar(by_type, x="reason_code", y="money_at_risk",
                       title=f"Money at risk by anomaly type (INR). {LABEL}"))
st.dataframe(by_type.round(0), hide_index=True)

st.subheader("Largest payroll anomalies")
top = (an[an.money_at_risk.notna()].sort_values("money_at_risk", ascending=False).head(15)
       [["result_id", "employee_id", "period", "reason_code", "reason_text",
         "money_at_risk", "anomaly_score"]])
st.dataframe(top.round(2), hide_index=True)

# 2. Forecast with 80% range
st.subheader("2. Forecast with 80% range")
st.write("Plain note: the shaded band is the range the model expects the value to fall in "
         "80% of the time. Future months have no actual values yet. " + LABEL + ".")
metric = st.selectbox("Metric", sorted(fc.metric.unique()))
dept = st.selectbox("Department", sorted(fc.department_id.unique()))
f = fc[(fc.metric == metric) & (fc.department_id == dept)].sort_values("forecast_month")
fig = go.Figure()
fig.add_scatter(x=f.forecast_month, y=f.upper_80, mode="lines", line=dict(width=0),
                showlegend=False)
fig.add_scatter(x=f.forecast_month, y=f.lower_80, mode="lines", line=dict(width=0),
                fill="tonexty", fillcolor="rgba(0,100,200,0.2)", name="80% range")
fig.add_scatter(x=f.forecast_month, y=f.forecast_value, mode="lines+markers", name="Forecast")
fig.update_layout(title=f"{LABEL}: {metric}, {dept}")
st.plotly_chart(fig)

# 3. Forecast error on past months (backtest)
st.subheader("3. Forecast error on past months (backtest)")
st.write("Plain note: each row compares a past forecast with the actual value that later "
         "happened. " + LABEL + ".")
known = bt[bt.actual.notna()]
if known.empty:
    st.info("No forecast month in this dataset has an actual value yet, so forecast error "
            "cannot be calculated from the data. " + LABEL + ".")
else:
    st.metric("Average absolute error (known months)", f"{known.abs_pct_error.mean():.2f}")
    st.dataframe(known[["department_id", "month", "forecast_value", "actual",
                        "abs_pct_error"]].round(2), hide_index=True)
st.dataframe(bt.sort_values("month")[["department_id", "month", "forecast_value",
                                      "actual", "status"]], hide_index=True)