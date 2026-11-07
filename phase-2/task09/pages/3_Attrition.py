import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

MIN_GROUP = 5   # minimum group size (same rule as Task 4)

st.set_page_config(page_title="Attrition", layout="wide")
st.title("Attrition analytics")
st.caption(f"Groups with fewer than {MIN_GROUP} people are hidden or combined so no individual can be identified.")

@st.cache_data
def q(sql):
    con = duckdb.connect("pulseiq.duckdb", read_only=True)
    try:
        return con.sql(sql).df()
    finally:
        con.close()

ex = q("SELECT * FROM dw.v_exits_monthly ORDER BY month")
ex["month"] = pd.to_datetime(ex["month"])
ex["year"] = ex["month"].dt.year
ten = q("SELECT * FROM dw.v_exit_tenure")
ten["year"] = pd.to_datetime(ten["exit_date"]).dt.year

# ---------- Sidebar filters ----------
ymin, ymax = int(ex["year"].min()), int(ex["year"].max())
y0, y1 = st.sidebar.slider("Years", ymin, ymax, (max(ymin, ymax - 2), ymax))
depts = sorted(ex["department"].unique())
chosen = st.sidebar.multiselect("Department", depts, default=depts)

e = ex[ex["year"].between(y0, y1) & ex["department"].isin(chosen)]
t = ten[ten["year"].between(y0, y1) & ten["department"].isin(chosen)].copy()
if e.empty:
    st.warning("Select at least one department.")
    st.stop()

# Privacy guard: hide everything if the selected group is too small
sel_hc = e.groupby("month")["avg_headcount"].sum().mean()
if sel_hc < MIN_GROUP:
    st.info(f"The selection has fewer than {MIN_GROUP} people, so results are hidden to protect individuals.")
    st.stop()

# =====================================================
# SECTION A: ACTUAL
# =====================================================
with st.container(border=True):
    st.header("Actual exits (what happened)")

    months = e["month"].nunique()
    tot = int(e["exits"].sum())
    vol = int(e["voluntary_exits"].sum())
    hc_sum = e["avg_headcount"].sum()
    annual = tot * 12 / hc_sum * 100 if hc_sum else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Exits in period", f"{tot:,}")
    k2.metric("Voluntary share", f"{vol / tot:.0%}" if tot else "n/a")
    k3.metric("Annual attrition (avg headcount)", f"{annual:.1f}%")
    k4.metric("Months covered", months)

    # Exits per month: voluntary vs other
    m = (e.groupby("month")[["voluntary_exits", "other_exits"]].sum().reset_index()
           .melt(id_vars="month", var_name="type", value_name="exits"))
    m["type"] = m["type"].map({"voluntary_exits": "Voluntary", "other_exits": "Other"})
    st.subheader("Exits per month")
    st.plotly_chart(px.bar(m, x="month", y="exits", color="type", barmode="stack"),
                    use_container_width=True)

    # Exits by department, with the minimum group size rule
    st.subheader("Exits by department")
    d = (e.groupby("department")
           .agg(exits=("exits", "sum"), voluntary=("voluntary_exits", "sum"),
                hc_sum=("avg_headcount", "sum")).reset_index())
    d["avg_headcount"] = d["hc_sum"] / months
    big = d[d["avg_headcount"] >= MIN_GROUP].copy()
    small = d[d["avg_headcount"] < MIN_GROUP]
    big["annual_attrition_pct"] = big["exits"] * 12 / big["hc_sum"] * 100
    rows = big[["department", "exits", "voluntary", "avg_headcount", "annual_attrition_pct"]]
    if not small.empty:
        sm_hc = small["hc_sum"].sum() / months
        if sm_hc >= MIN_GROUP:
            comb = pd.DataFrame([{
                "department": f"Small departments combined ({len(small)})",
                "exits": small["exits"].sum(), "voluntary": small["voluntary"].sum(),
                "avg_headcount": sm_hc,
                "annual_attrition_pct": small["exits"].sum() * 12 / small["hc_sum"].sum() * 100}])
            rows = pd.concat([rows, comb], ignore_index=True)
        else:
            st.info(f"{len(small)} department(s) with fewer than {MIN_GROUP} people are not shown.")
    rows = rows.sort_values("annual_attrition_pct", ascending=False)
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.bar(rows, x="annual_attrition_pct", y="department", orientation="h",
                           labels={"annual_attrition_pct": "Annual attrition %"}),
                    use_container_width=True)
    c2.dataframe(rows.round(1), hide_index=True, use_container_width=True)

    # Tenure at exit
    st.subheader("Tenure at exit")
    if len(t) < MIN_GROUP:
        st.info(f"Fewer than {MIN_GROUP} exits in this selection, so tenure is hidden.")
    else:
        t["band"] = pd.cut(t["tenure_years"], [-0.01, 1, 2, 5, 10, 100],
                           labels=["<1 yr", "1-2 yrs", "2-5 yrs", "5-10 yrs", "10+ yrs"])
        tb = t.groupby(["band", "exit_type"], observed=True).size().reset_index(name="exits")
        a, b = st.columns([1, 2])
        a.metric("Median tenure at exit", f"{t['tenure_years'].median():.1f} yrs")
        a.metric("Left within 2 years", f"{(t['tenure_years'] < 2).mean():.0%}")
        b.plotly_chart(px.bar(tb, x="band", y="exits", color="exit_type", barmode="stack"),
                       use_container_width=True)
        st.caption("Exit type is the employment status recorded for the leaver.")

# =====================================================
# SECTION B: PREDICTED
# =====================================================
st.write("")
with st.container(border=True):
    st.header("Predicted, not certain")
    st.warning("This section shows model PREDICTIONS about groups of people. "
               "They are not facts and not decisions about anyone.")

    rk = q("SELECT * FROM dw.v_risk_by_dept")
    rk = rk[rk["department"].isin(chosen)]
    if rk.empty:
        st.info("No predictions for this selection.")
    else:
        mv = q("SELECT DISTINCT model_version, model_note FROM dw.fact_attrition_risk")
        st.caption(f"Predictions as of {pd.to_datetime(rk['as_of_date'].iloc[0]).date()} "
                   f"| Model: {mv['model_version'].iloc[0]} | {mv['model_note'].iloc[0]}")
        keep = rk[rk["scored"] >= MIN_GROUP].copy()
        hidden = len(rk) - len(keep)
        if keep.empty:
            st.info(f"Every department in this selection has fewer than {MIN_GROUP} scored people, so risk is hidden.")
        else:
            tot_sc = int(keep["scored"].sum())
            st.metric("Predicted share in the High-risk band", f"{keep['high'].sum() / tot_sc:.1%}")
            sh = keep.assign(High=keep["high"] / keep["scored"],
                             Medium=keep["medium"] / keep["scored"],
                             Low=keep["low"] / keep["scored"])
            long = sh.melt(id_vars="department", value_vars=["High", "Medium", "Low"],
                           var_name="Predicted band", value_name="share")
            fig = px.bar(long, x="share", y="department", color="Predicted band",
                         orientation="h", barmode="stack",
                         category_orders={"Predicted band": ["High", "Medium", "Low"]},
                         color_discrete_map={"High": "#d62728", "Medium": "#ffb347", "Low": "#c7dcef"})
            fig.update_xaxes(tickformat=".0%", title="Predicted share of people in each band")
            st.plotly_chart(fig, use_container_width=True)
            if hidden:
                st.caption(f"{hidden} department(s) with fewer than {MIN_GROUP} scored people are hidden.")

        rs = q("SELECT * FROM dw.v_risk_reasons")
        rs = rs[(rs["risk_band"].str.upper() == "HIGH") & (rs["mentions"] >= MIN_GROUP)]
        if not rs.empty:
            st.subheader("Most common predicted drivers in the High-risk band (company-wide)")
            rs = rs.sort_values("mentions")
            st.plotly_chart(px.bar(rs, x="mentions", y="reason", orientation="h"),
                            use_container_width=True)

    with st.expander("What this prediction is and is not", expanded=True):
        st.markdown(f"""
**What it is**
- A simple baseline model's estimate of how likely groups of people are to leave in the next 12 months.
- A starting point for a supportive conversation, such as workload, pay or growth.

**What it is not**
- Not a fact: most people in a High band will not leave, and some in a Low band will.
- Not a decision tool: never use it for hiring, firing, pay or promotion.
- Not about individuals: only groups of at least {MIN_GROUP} people are shown, and no names or IDs.
- The drivers show what the model used, not proven causes.
""")