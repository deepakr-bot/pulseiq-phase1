import json

import duckdb
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

MIN_GROUP = 5   # minimum group size (same rule as Task 4 and Task 9)

# Review date used in the recommendation sentences. Change it if you need a different date.
REVIEW_DATE = "15 Dec 2026"

# Action sentences. {amount} = post-freeze overspend in rupees,
# {monthly} = average overspend per month after the freeze, {date} = REVIEW_DATE.
ACTIONS = {
    "Data & AI": (
        "Review the {amount} post-freeze overspend (about {monthly} a month) against pay rates "
        "and open roles, and reset the H2 budget with finance by {date}."
    ),
    "Product & Design": (
        "Hold backfills for open roles until the revised budget is approved, and review the "
        "{amount} post-freeze overspend (about {monthly} a month) with finance by {date}."
    ),
}

st.set_page_config(page_title="Budget vs actual", layout="wide")
st.title("Budget versus actual and KPI targets")


@st.cache_data
def q(sql):
    con = duckdb.connect("pulseiq.duckdb", read_only=True)
    try:
        return con.sql(sql).df()
    finally:
        con.close()


def inr(x):
    s = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1e7:
        return f"{s}₹{x / 1e7:,.2f} Cr"
    if x >= 1e5:
        return f"{s}₹{x / 1e5:,.2f} L"
    return f"{s}₹{x:,.0f}"


def variance_pct(frame):
    """Variance % = (Actual - Budget) / Budget x 100, for a group of rows."""
    b = frame["budget"].sum()
    return (frame["actual"].sum() - b) / b * 100


try:
    v = q("""SELECT month, department_id, department, employees_paid, budget, actual, variance, variance_pct
             FROM dw.v_payroll_variance WHERE actual IS NOT NULL AND budget IS NOT NULL""")
    size = q("SELECT department_id, avg_employees FROM dw.v_payroll_dept_size")
except Exception:
    st.error("The budget views do not exist yet. Close Streamlit, run `python create_budget_views.py`, "
             "then start the app again.")
    st.stop()

try:
    cfg = json.load(open("budget_rules.json", encoding="utf-8"))
except Exception:
    cfg = {}
label = {"gross_pay": "gross pay", "net_pay": "net pay", "employer_cost": "employer cost"}.get(
    cfg.get("actual_measure"), "payroll cost")

# ---------- Minimum group size rule ----------
ok = set(size.loc[size["avg_employees"] >= MIN_GROUP, "department_id"])
n_hidden = len(size) - len(ok)
v = v[v["department_id"].isin(ok) & (v["employees_paid"] >= MIN_GROUP)].copy()
if v.empty:
    st.warning("No data to show.")
    st.stop()

# ---------- Sign rule box (always visible) ----------
with st.expander("Rules used on this page (read first)", expanded=True):
    st.markdown(f"""
- **Sign rule: Variance = Actual − Budget.** A **positive** variance means **overspend** (actual is above budget) and is shown in **red**. A **negative** variance means **underspend** and is shown in **green**.
- **Variance %** = Variance ÷ Budget × 100.
- **Actual** = {label} from the cleaned payroll data (the 4 bad rows found in Task 9 are excluded). **Budget** = `budget_payroll_dept_month`.
- Only months that have both a budget and an actual are compared.
- **Ranking:** departments are ranked from the biggest overspend to the biggest underspend.
- **Privacy:** only department totals are shown. Departments with fewer than {MIN_GROUP} people ({n_hidden} department(s)) are hidden.
""")

# ---------- Sidebar ----------
months = sorted(v["month"].unique())
m0, m1 = st.sidebar.select_slider("Months", options=months, value=(months[0], months[-1]))
depts = sorted(v["department"].unique())
chosen = st.sidebar.multiselect("Department", depts, default=depts)
rank_by = st.sidebar.radio("Rank departments by", ["Variance (₹)", "Variance (%)"])
freeze = st.sidebar.selectbox("Mark a hiring-freeze month (optional)", ["None"] + months)

d = v[v["month"].between(m0, m1) & v["department"].isin(chosen)]
if d.empty:
    st.warning("Select at least one department.")
    st.stop()

# ---------- KPI cards ----------
tb, ta = d["budget"].sum(), d["actual"].sum()
tv = ta - tb
k1, k2, k3, k4 = st.columns(4)
k1.metric("Budget", inr(tb))
k2.metric(f"Actual ({label})", inr(ta))
k3.metric("Variance (actual − budget)", inr(tv), delta=f"{tv / tb * 100:+.2f}%", delta_color="inverse")
k4.metric("Departments over budget",
          f"{int((d.groupby('department')['variance'].sum() > 0).sum())} of {d['department'].nunique()}")

# ---------- Monthly trend ----------
st.header("Budget versus actual by month")
mo = d.groupby("month", as_index=False).agg(budget=("budget", "sum"), actual=("actual", "sum"))
mo["variance"] = mo["actual"] - mo["budget"]
mo["variance_pct"] = mo["variance"] / mo["budget"] * 100
long = mo.melt(id_vars="month", value_vars=["budget", "actual"], var_name="measure", value_name="amount")
long["measure"] = long["measure"].map({"budget": "Budget", "actual": "Actual"})
c1, c2 = st.columns(2)
f1 = px.line(long, x="month", y="amount", color="measure", markers=True, title="Budget and actual (₹ per month)")
f1.update_yaxes(tickformat=",.0f")
mo["status"] = np.where(mo["variance"] > 0, "Overspend", "Underspend")
f2 = px.bar(mo, x="month", y="variance_pct", color="status", title="Variance % by month (positive = overspend)",
            color_discrete_map={"Overspend": "#d62728", "Underspend": "#2ca02c"})
f2.update_yaxes(title="variance %")
if freeze != "None" and freeze in set(mo["month"]):
    for f in (f1, f2):
        f.add_shape(type="line", x0=freeze, x1=freeze, y0=0, y1=1, xref="x", yref="paper",
                    line=dict(color="black", dash="dot"))
        f.add_annotation(x=freeze, y=1, xref="x", yref="paper", text="hiring freeze", showarrow=False, yshift=10)
c1.plotly_chart(f1, width="stretch")
c2.plotly_chart(f2, width="stretch")

# ---------- Ranking ----------
st.header("Ranking: biggest overspend first")
rk = d.groupby("department", as_index=False).agg(budget=("budget", "sum"), actual=("actual", "sum"),
                                                 months=("month", "nunique"))
over = d.assign(o=(d["variance"] > 0).astype(int)).groupby("department")["o"].sum().rename("months_over").reset_index()
rk = rk.merge(over, on="department")
rk["variance"] = rk["actual"] - rk["budget"]
rk["variance_pct"] = rk["variance"] / rk["budget"] * 100
rk = rk.sort_values("variance" if rank_by.startswith("Variance (₹") else "variance_pct", ascending=False)
rk.insert(0, "rank", range(1, len(rk) + 1))
rk["status"] = np.where(rk["variance"] > 0, "Overspend", "Underspend")
r1, r2 = st.columns([3, 2])
fig = px.bar(rk.sort_values("variance" if rank_by.startswith("Variance (₹") else "variance_pct"),
             x="variance" if rank_by.startswith("Variance (₹") else "variance_pct", y="department", orientation="h",
             color="status", color_discrete_map={"Overspend": "#d62728", "Underspend": "#2ca02c"},
             labels={"variance": "variance (₹)", "variance_pct": "variance %"})
r1.plotly_chart(fig, width="stretch")
tab = rk[["rank", "department", "budget", "actual", "variance", "variance_pct", "months_over", "months"]].copy()
tab.columns = ["rank", "department", "budget", "actual", "variance", "variance %", "months over budget", "months"]
r2.dataframe(tab.round({"budget": 0, "actual": 0, "variance": 0, "variance %": 2}),
             hide_index=True, width="stretch")

# ---------- Heatmap ----------
st.header("Heatmap: variance % by department and month")
hm = d.pivot_table(index="department", columns="month", values="variance_pct", aggfunc="mean")
st.plotly_chart(px.imshow(hm, aspect="auto", color_continuous_scale="RdYlGn_r", color_continuous_midpoint=0,
                          labels=dict(color="variance %")), width="stretch")

# ---------- Hiring freeze ----------
st.header("Hiring freeze: reading variance fairly")
if freeze == "None":
    st.info("Pick a hiring-freeze month in the sidebar to compare variance before and after it.")
else:
    a = d[d["month"] < freeze]
    b = d[d["month"] >= freeze]
    if a.empty or b.empty:
        st.info("Pick a month inside the selected range, so that there are months before and after it.")
    else:
        f1c, f2c = st.columns(2)
        f1c.metric(f"Variance % before {freeze}", f"{variance_pct(a):+.2f}%")
        f2c.metric(f"Variance % from {freeze}", f"{variance_pct(b):+.2f}%")
st.caption("If the budget was never updated after a hiring freeze, the variance after the freeze compares real "
           "spending with an outdated plan. Read it together with this before and after view, and ask finance "
           "for the revised budget before judging a department.")

# ---------- KPI traffic lights ----------
st.header("KPI targets and traffic lights")
try:
    ks = q("SELECT * FROM dw.v_kpi_status")
except Exception:
    ks = None
    st.info("The KPI view does not exist yet. Close Streamlit, run `python create_kpi_view.py`, "
            "then start the app again.")

if ks is not None:
    EM = {"Green": "🟢", "Amber": "🟡", "Red": "🔴", "Grey": "⚪"}
    ks = ks[ks["department"].isin(chosen)]
    if ks.empty:
        st.info("No KPI targets for the selected departments.")
    else:
        with st.expander("Traffic-light rules (read first)", expanded=True):
            lines = ["- Targets come from `kpi_targets` (one target per KPI, department and month). "
                     "That table has targets only, so the amber band below is a rule I chose and applied to every department."]
            lines += [f"- **{r.kpi}**: {r.rule}" for r in ks.drop_duplicates("kpi").itertuples()]
            lines += ["- ⚪ Grey: no target, or no data (for example a group below the minimum size)."]
            st.markdown("\n".join(lines))

        kmonths = sorted(ks["month"].unique())
        km = st.selectbox("KPI month", kmonths, index=len(kmonths) - 1)
        cur = ks[ks["month"] == km].copy()
        cs = cur["status"].value_counts()
        a_, b_, c_, e_ = st.columns(4)
        a_.metric("🟢 Green", int(cs.get("Green", 0)))
        b_.metric("🟡 Amber", int(cs.get("Amber", 0)))
        c_.metric("🔴 Red", int(cs.get("Red", 0)))
        e_.metric("⚪ Grey", int(cs.get("Grey", 0)))

        def show(r):
            if pd.isna(r["target"]):
                return f"{EM['Grey']} no target"
            if pd.isna(r["actual"]):
                return f"{EM['Grey']} no data"
            dec = 3 if r["kpi"] == "Attendance rate" else 2
            return f"{EM[r['status']]} {r['actual']:.{dec}f} (target {r['target']:.{dec}f})"

        cur["shown"] = cur.apply(show, axis=1)
        grid = cur.pivot_table(index="department", columns="kpi", values="shown", aggfunc="first")
        st.dataframe(grid, width="stretch")

        tot = ks.groupby(["kpi", "status"]).size().reset_index(name="department-months")
        st.plotly_chart(
            px.bar(tot, x="kpi", y="department-months", color="status", barmode="stack",
                   color_discrete_map={"Green": "#2ca02c", "Amber": "#ffb347", "Red": "#d62728", "Grey": "#bbbbbb"},
                   title="Status of all department-months (selected departments)"),
            width="stretch")

# ---------- Recommendations ----------
st.header("Recommendations: top 2 overspend departments")
if freeze == "None":
    st.info("Pick a hiring-freeze month in the sidebar to see the before and after variance for the recommendations.")
else:
    top2 = rk.sort_values("variance", ascending=False).head(2)
    for _, row in top2.iterrows():
        dept = row["department"]
        sub = d[d["department"] == dept]
        pre = sub[sub["month"] < freeze]
        post = sub[sub["month"] >= freeze]
        if pre.empty or post.empty:
            st.write(f"**{dept}:** needs months both before and after {freeze} in the selected range.")
            continue
        pp = variance_pct(pre)
        pq = variance_pct(post)
        post_total = post["variance"].sum()
        monthly = post_total / post["month"].nunique()
        template = ACTIONS.get(dept, "[ADD AN ACTION FOR THIS DEPARTMENT IN ACTIONS ABOVE]")
        action = template.format(amount=inr(post_total), monthly=f"₹{monthly:,.0f}", date=REVIEW_DATE)
        if pq > 0:
            lead = "The overspend that began after the freeze is real and needs action: "
        else:
            lead = ("Part of the variance may come from the stale budget. Ask finance to reset the budget "
                    "before judging this department. Action: ")
        st.markdown(
            f"**{dept}:** Variance was {pp:+.2f}% before the hiring freeze and {pq:+.2f}% from {freeze}. "
            f"The budget was not updated after the freeze, so the post-freeze figure compares actual "
            f"payroll with an outdated plan. {lead}{action}"
        )

st.caption("No individual salary is shown: every number is a total for a group of at least "
           f"{MIN_GROUP} people.")