import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="PulseIQ live dashboard", layout="wide")
DATA = Path(__file__).resolve().parent / "data"


@st.cache_data
def load():
    company = pd.read_csv(DATA / "company_monthly.csv")
    dept = pd.read_csv(DATA / "department_monthly.csv")
    meta = json.loads((DATA / "meta.json").read_text())
    return company, dept, meta


company, dept, meta = load()

st.sidebar.title("PulseIQ")
page = st.sidebar.radio("Go to", ["Home", "Company", "Departments"])
st.sidebar.caption(f"Data cut-off: {meta['data_cutoff']}")
st.sidebar.caption(f"Aggregates only. Departments with fewer than "
                   f"{meta['min_group_size']} people are not shown.")

if page == "Home":
    st.title("PulseIQ: live dashboard")
    st.write("Company finance and people measures, published as aggregates.")
    latest = company.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest month", latest["month"])
    c2.metric("Headcount", f"{int(latest['headcount']):,}")
    c3.metric("Revenue (INR)", f"{latest['revenue'] / 1e6:,.1f} M")
    c4.metric("Operating margin", f"{latest['operating_margin_pct']:.1f} %")
    st.write("Open **Company** or **Departments** in the menu on the left.")

elif page == "Company":
    st.title("Company measures by month")
    months = company["month"].tolist()
    chosen = st.multiselect("Months", months, default=months[-12:])
    view = company[company["month"].isin(chosen)]
    st.plotly_chart(px.line(view, x="month", y=["revenue", "net_profit_inr"], markers=True,
                            title="Revenue and net profit (INR)"))
    st.plotly_chart(px.line(view, x="month", y="operating_margin_pct", markers=True,
                            title="Operating margin %"))
    st.dataframe(view, hide_index=True)

else:
    st.title("Departments")
    month = st.selectbox("Month", sorted(dept["month"].unique(), reverse=True))
    view = dept[dept["month"] == month].sort_values("headcount", ascending=False)
    st.write(f"Departments shown for {month}: {len(view)}")
    st.plotly_chart(px.bar(view, x="department_name", y="headcount",
                           title="Headcount by department"))
    st.dataframe(view[["department_name", "headcount", "attendance_rate",
                       "overtime_share_pct", "attrition_rate_pct"]],
                 hide_index=True)