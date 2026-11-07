import duckdb
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Attendance & Leave", layout="wide")
st.title("Attendance and leave trends")

@st.cache_data
def q(sql):
    con = duckdb.connect("pulseiq.duckdb", read_only=True)
    try:
        return con.sql(sql).df()
    finally:
        con.close()

att = q("SELECT * FROM dw.v_attendance_monthly ORDER BY year_month")
depts = sorted(att["department"].unique())
chosen = st.sidebar.multiselect("Department", depts, default=depts)
df = att[att["department"].isin(chosen)]
if df.empty:
    st.warning("Select at least one department.")
    st.stop()

hol = q("SELECT * FROM dw.v_holidays_monthly")

# Rate = total present / total scheduled (ratio of sums)
m = (df.groupby("year_month")
       .agg(present=("present_days", "sum"), scheduled=("scheduled_days", "sum"),
            late=("late_arrivals", "sum"), ot=("overtime_hours", "sum"))
       .reset_index())
m["attendance_rate"] = m["present"] / m["scheduled"]
m = m.merge(hol, on="year_month", how="left")

k1, k2, k3 = st.columns(3)
k1.metric("Average attendance rate", f"{m['present'].sum() / m['scheduled'].sum():.1%}")
k2.metric("Late arrivals (total)", f"{int(m['late'].sum()):,}")
k3.metric("Overtime hours (total)", f"{m['ot'].sum():,.0f}")

st.subheader("Attendance rate by month")
fig = px.line(m, x="year_month", y="attendance_rate", markers=True)
for _, r in m[m["holidays"] > 0].iterrows():
    fig.add_vrect(x0=r["year_month"], x1=r["year_month"],
                  line_dash="dot", line_color="orange", opacity=0.6)
fig.update_yaxes(tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)
st.caption("Orange dotted lines = months that contain public holidays or long weekends.")

st.subheader("Heatmap: attendance rate by department and month")
g = (df.groupby(["department", "year_month"])
       .agg(p=("present_days", "sum"), s=("scheduled_days", "sum")).reset_index())
g["rate"] = g["p"] / g["s"]
hm = g.pivot(index="department", columns="year_month", values="rate")
st.plotly_chart(px.imshow(hm, aspect="auto", color_continuous_scale="RdYlGn",
                          labels=dict(color="Rate")), use_container_width=True)

c1, c2 = st.columns(2)
c1.subheader("Late arrivals by month")
c1.plotly_chart(px.bar(m, x="year_month", y="late"), use_container_width=True)
c2.subheader("Overtime hours by month")
c2.plotly_chart(px.line(m, x="year_month", y="ot", markers=True), use_container_width=True)

st.subheader("Leave days by type")
leave = q("SELECT * FROM dw.v_leave_monthly ORDER BY year_month")
st.plotly_chart(px.bar(leave, x="year_month", y="leave_days", color="leave_type"),
                use_container_width=True)
st.caption("Leave is counted in the month it starts, so long leaves such as maternity leave appear in their start month and not across the months the person is away. Attendance charts count actual days present.")