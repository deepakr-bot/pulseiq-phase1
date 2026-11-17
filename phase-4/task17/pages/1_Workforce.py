import pandas as pd
import plotly.express as px
import streamlit as st
from db import q

st.set_page_config(page_title="Workforce", layout="wide")
BLUE, ORANGE, GREY = "#1f77b4", "#ff7f0e", "#bdbdbd"

@st.cache_data
def load():
    hc = q("""SELECT h.department_id, d.department_name, h.month, h.headcount
              FROM m01_headcount h JOIN v5_department d USING (department_id)""")
    hx = q("""SELECT i.department_id, i.month, i.hires, e.exits
              FROM m02_hires i JOIN m03_exits e USING (department_id, month)""")
    att = q("SELECT month, attrition_12m_pct FROM v5_company_attrition_12m")
    tier = q("SELECT city_tier, headcount FROM v5_headcount_by_location_tier ORDER BY tier_number")
    mode = q("SELECT work_mode, headcount FROM v5_headcount_by_work_mode")
    for df in (hc, hx, att):
        df["month"] = pd.to_datetime(df["month"])
        df["ym"] = df["month"].dt.strftime("%Y-%m")
    return hc, hx, att, tier, mode

hc, hx, att, tier, mode = load()

st.title("Workforce and headcount")

# ---- filters ----
labels = sorted(hc["ym"].unique())
depts = sorted(hc["department_name"].unique())
st.sidebar.header("Filters")
sel = st.sidebar.multiselect("Department", depts, default=depts)
start, end = st.sidebar.select_slider("Date range (months)", options=labels,
                                      value=(labels[-12], labels[-1]))
if not sel:
    st.warning("Select at least one department.")
    st.stop()

ids = hc[hc.department_name.isin(sel)].department_id.unique()
hc_f = hc[hc.department_name.isin(sel) & (hc.ym >= start) & (hc.ym <= end)]
hx_f = hx[hx.department_id.isin(ids) & (hx.ym >= start) & (hx.ym <= end)]
if hc_f.empty:
    st.warning("No data for this selection.")
    st.stop()

trend = hc_f.groupby("ym", as_index=False)["headcount"].sum()
now, first = int(trend.headcount.iloc[-1]), int(trend.headcount.iloc[0])
change = 100 * (now - first) / first
hires, exits = int(hx_f.hires.sum()), int(hx_f.exits.sum())
a = att[att.ym == end]
attr = float(a.attrition_12m_pct.iloc[0]) if len(a) else None

# ---- KPI cards ----
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Headcount ({end})", f"{now:,}", f"{change:+.1f}% vs {start}", delta_color="off")
c2.metric("Hires in period", f"{hires:,}")
c3.metric("Exits in period", f"{exits:,}")
c4.metric("12-month attrition (company)", f"{attr:.2f}%" if attr is not None else "n/a")

# ---- headcount trend ----
verb = "grew" if change > 0 else "fell" if change < 0 else "stayed flat"
fig = px.line(trend, x="ym", y="headcount", markers=True)
fig.update_traces(line_color=BLUE)
fig.update_layout(title=f"Headcount {verb} {abs(change):.1f}% from {start} to {end}",
                  xaxis_title="", yaxis_title="People")
st.plotly_chart(fig, use_container_width=True)
st.caption(f"Insight: {first:,} people in {start} and {now:,} in {end}, with {hires:,} hires and {exits:,} exits during the period.")

# ---- department breakdown ----
dd = (hc_f[hc_f.ym == end].groupby("department_name", as_index=False)["headcount"].sum()
      .sort_values("headcount"))
if not dd.empty:
    top, small = dd.iloc[-1], dd.iloc[0]
    share = 100 * top.headcount / dd.headcount.sum()
    dd["color"] = [ORANGE if n == top.department_name else GREY for n in dd.department_name]
    fig2 = px.bar(dd, x="headcount", y="department_name", orientation="h",
                  color="color", color_discrete_map="identity")
    fig2.update_layout(title=f"{top.department_name} is the largest department with {int(top.headcount)} people ({share:.0f}%)",
                       xaxis_title="People", yaxis_title="", showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)
    st.caption(f"Insight: the smallest department in view is {small.department_name} with {int(small.headcount)} people.")

# ---- location tier and work mode (latest snapshot, all departments) ----
def snapshot(df, cat, title_text):
    df = df.sort_values("headcount", ascending=False).reset_index(drop=True)
    total = int(df.headcount.sum())
    top = df.iloc[0]
    pct = 100 * top.headcount / total
    df["color"] = [ORANGE if i == 0 else GREY for i in range(len(df))]
    fig = px.bar(df, x=cat, y="headcount", color="color", color_discrete_map="identity")
    fig.update_layout(title=title_text.format(name=top[cat], pct=pct),
                      xaxis_title="", yaxis_title="People", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    second = f", the next largest has {int(df.headcount.iloc[1]):,}" if len(df) > 1 else ""
    st.caption(f"Insight: {int(top.headcount):,} of {total:,} current employees are in {top[cat]}{second}.")

l, r = st.columns(2)
with l:
    snapshot(tier, "city_tier", "{name} holds {pct:.0f}% of people")
with r:
    snapshot(mode, "work_mode", "{name} is the most common work mode ({pct:.0f}%)")
st.caption("Location tier and work mode show the latest snapshot for all departments.")
st.caption("Note: the headcount card uses m01_headcount, which hides departments with fewer than 5 people (privacy rule). Location tier and work mode count all current employees, so the totals differ by 1.")