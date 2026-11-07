import json
import duckdb
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

MIN_DUE = 10   # on-time rates based on fewer finished tasks are marked "Low sample"

st.set_page_config(page_title="Team productivity", layout="wide")
st.title("Team productivity")


@st.cache_data
def load(sql):
    con = duckdb.connect("pulseiq.duckdb", read_only=True)
    try:
        return con.sql(sql).df()
    finally:
        con.close()


ts = load("SELECT * FROM dw.v_team_sprint")
try:
    rules = json.load(open("team_rules.json", encoding="utf-8"))
except Exception:
    rules = {}
cycle_start = rules.get("cycle_start", "started date")

# ---------- Rules box (visible) ----------
with st.expander("Rules used on this page", expanded=True):
    st.markdown(f"""
- **Velocity** = story points of tasks with status Done, per sprint (average per sprint when "All sprints" is selected).
- **Cycle time** = days from the **{cycle_start}** to the done date, Done tasks only. Missing or negative dates are ignored.
- **On-time rate** = Done tasks finished on or before the due date / Done tasks that have a due date. Rates based on fewer than {MIN_DUE} tasks are marked "Low sample".
- **Cancelled tasks** are **excluded from every metric** (planned work, velocity, cycle time, on-time, blocked and reopened). They are only counted, for context.
- **Blocked** and **reopened** tasks are counted once per task and shown as a share of planned (non-cancelled) tasks.
- Teams differ in size, work type and sprint length, so compare teams with the context columns (tasks and points per task), not velocity alone.
""")

# ---------- Sidebar ----------
sp = ts[["sprint_id", "sprint", "sprint_start"]].drop_duplicates("sprint_id")
sp = sp.sort_values(["sprint_start", "sprint_id"], na_position="last").reset_index(drop=True)
sp["label"] = sp["sprint"].astype(str)
dup = sp["label"].duplicated(keep=False)
sp.loc[dup, "label"] = sp.loc[dup, "label"] + " (" + sp.loc[dup, "sprint_id"].astype(str) + ")"

choice = st.sidebar.selectbox("Sprint", ["All sprints"] + sp["label"].tolist())
teams = sorted(ts["team"].unique())
chosen = st.sidebar.multiselect("Team", teams, default=teams)

d = ts[ts["team"].isin(chosen)]
if choice != "All sprints":
    sid = sp.loc[sp["label"] == choice, "sprint_id"].iloc[0]
    d = d[d["sprint_id"] == sid]
if d.empty or d["planned"].sum() == 0:
    st.warning("No tasks for this selection.")
    st.stop()


def rollup(df, by):
    df = df.assign(has_work=(df["planned"] > 0).astype(int))
    g = df.groupby(by).agg(
        sprints=("has_work", "sum"), planned=("planned", "sum"), cancelled=("cancelled", "sum"),
        done=("done", "sum"), points_done=("points_done", "sum"), cycle_sum=("cycle_sum", "sum"),
        cycle_n=("cycle_n", "sum"), due_done=("due_done", "sum"), on_time_done=("on_time_done", "sum"),
        blocked=("blocked", "sum"), reopened=("reopened", "sum")).reset_index()
    g["velocity"] = g["points_done"] / g["sprints"].where(g["sprints"] > 0)
    g["avg_cycle_days"] = g["cycle_sum"] / g["cycle_n"].where(g["cycle_n"] > 0)
    g["on_time_pct"] = g["on_time_done"] / g["due_done"].where(g["due_done"] > 0) * 100
    g["blocked_pct"] = g["blocked"] / g["planned"].where(g["planned"] > 0) * 100
    g["reopened_pct"] = g["reopened"] / g["planned"].where(g["planned"] > 0) * 100
    g["points_per_task"] = g["points_done"] / g["done"].where(g["done"] > 0)
    return g


comp = rollup(d.assign(all="All"), ["all"]).iloc[0]
bt = rollup(d, ["team"])
per = "points" if choice != "All sprints" else "points per sprint"

# ---------- KPIs ----------
st.subheader("Overview: " + ("all sprints" if choice == "All sprints" else choice))
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Avg team velocity (points per team per sprint)", f"{comp['velocity']:,.0f}")
k2.metric("Avg cycle time", f"{comp['avg_cycle_days']:.1f} days")
k3.metric("On-time rate", f"{comp['on_time_pct']:.0f}%")
k4.metric("Blocked tasks", f"{comp['blocked_pct']:.1f}%")
k5.metric("Reopened tasks", f"{comp['reopened_pct']:.1f}%")
k6.metric("Cancelled (excluded)", f"{int(comp['cancelled']):,}")

# ---------- Per team ----------
st.header("By team")
c1, c2, c3 = st.columns(3)
v = bt.sort_values("velocity")
c1.plotly_chart(px.bar(v, x="velocity", y="team", orientation="h",
                       title=f"Velocity ({per})", labels={"velocity": per}),
                use_container_width=True)
o = bt.assign(sample=np.where(bt["due_done"] >= MIN_DUE, "OK", "Low sample")).sort_values("on_time_pct")
c2.plotly_chart(px.bar(o, x="on_time_pct", y="team", orientation="h", color="sample",
                       color_discrete_map={"OK": "#1f77b4", "Low sample": "#bbbbbb"},
                       title="On-time rate (%)", labels={"on_time_pct": "%"}),
                use_container_width=True)
c3.plotly_chart(px.bar(bt.sort_values("avg_cycle_days"), x="avg_cycle_days", y="team", orientation="h",
                       title="Average cycle time (days)", labels={"avg_cycle_days": "days"}),
                use_container_width=True)

# ---------- Blocked and reopened ----------
st.header("Blocked and reopened work")
bt["Reopened vs company"] = np.where(bt["reopened_pct"] > comp["reopened_pct"], "Above company rate", "At or below")
bt["Blocked vs company"] = np.where(bt["blocked_pct"] > comp["blocked_pct"], "Above company rate", "At or below")
red = {"Above company rate": "#d62728", "At or below": "#c7c7c7"}
b1, b2 = st.columns(2)
b1.plotly_chart(px.bar(bt.sort_values("reopened_pct"), x="reopened_pct", y="team", orientation="h",
                       color="Reopened vs company", color_discrete_map=red,
                       title=f"Reopened tasks (% of planned), company {comp['reopened_pct']:.1f}%",
                       labels={"reopened_pct": "%"}), use_container_width=True)
b2.plotly_chart(px.bar(bt.sort_values("blocked_pct"), x="blocked_pct", y="team", orientation="h",
                       color="Blocked vs company", color_discrete_map=red,
                       title=f"Blocked tasks (% of planned), company {comp['blocked_pct']:.1f}%",
                       labels={"blocked_pct": "%"}), use_container_width=True)

# ---------- Per sprint ----------
st.header("By sprint")
team_pick = st.selectbox("Team for the sprint trend", ["All selected teams"] + chosen)
tr = ts[ts["team"].isin(chosen if team_pick == "All selected teams" else [team_pick])]
s = tr.groupby(["sprint_id", "sprint", "sprint_start"], dropna=False).agg(
    points_done=("points_done", "sum"), due_done=("due_done", "sum"), on_time_done=("on_time_done", "sum"),
    cycle_sum=("cycle_sum", "sum"), cycle_n=("cycle_n", "sum"), planned=("planned", "sum"),
    blocked=("blocked", "sum"), reopened=("reopened", "sum")).reset_index()
s = s.sort_values(["sprint_start", "sprint_id"], na_position="last")
s["on_time_pct"] = s["on_time_done"] / s["due_done"].where(s["due_done"] > 0) * 100
s["avg_cycle_days"] = s["cycle_sum"] / s["cycle_n"].where(s["cycle_n"] > 0)
order = s["sprint"].astype(str).tolist()
s["sprint"] = s["sprint"].astype(str)
t1, t2 = st.columns(2)
t1.plotly_chart(px.bar(s, x="sprint", y="points_done", title="Velocity per sprint (points)",
                       category_orders={"sprint": order}), use_container_width=True)
t2.plotly_chart(px.line(s, x="sprint", y="on_time_pct", markers=True, title="On-time rate per sprint (%)",
                        category_orders={"sprint": order}), use_container_width=True)
t3, t4 = st.columns(2)
t3.plotly_chart(px.line(s, x="sprint", y="avg_cycle_days", markers=True, title="Average cycle time per sprint (days)",
                        category_orders={"sprint": order}), use_container_width=True)
sb = s.melt(id_vars=["sprint"], value_vars=["blocked", "reopened"], var_name="type", value_name="tasks")
t4.plotly_chart(px.bar(sb, x="sprint", y="tasks", color="type", barmode="group",
                       title="Blocked and reopened tasks per sprint",
                       color_discrete_map={"blocked": "#ff7f0e", "reopened": "#d62728"},
                       category_orders={"sprint": order}), use_container_width=True)

# ---------- Table ----------
st.header("Team table (with context)")
tab = bt[["team", "planned", "cancelled", "done", "points_done", "points_per_task", "velocity",
          "avg_cycle_days", "on_time_pct", "due_done", "blocked_pct", "reopened_pct"]].round(1)
tab = tab.rename(columns={"planned": "planned tasks", "points_done": "points done",
                          "points_per_task": "points per task", "velocity": f"velocity ({per})",
                          "avg_cycle_days": "cycle days", "on_time_pct": "on-time %",
                          "due_done": "done with due date", "blocked_pct": "blocked %",
                          "reopened_pct": "reopened %"})
st.dataframe(tab.sort_values("planned tasks", ascending=False), hide_index=True, use_container_width=True)
st.caption("No individual people are shown: all numbers are per team or per sprint.")