from pathlib import Path
import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Self-Service KPI Explorer", layout="wide")

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(BASE_DIR / "pulseiq.duckdb")
EXCEL_PATH = BASE_DIR / "PulseIQ_Dataset.xlsx"

# Look for demo_users.csv in task17 or 05_Starter
USER_PATHS = [
    BASE_DIR / "demo_users.csv",
    BASE_DIR / "05_Starter" / "demo_users.csv",
    BASE_DIR.parent / "05_Starter" / "demo_users.csv",
]

MIN_GROUP_SIZE = 5

ROLE_PERMISSIONS = {
    "ADMIN": {
        "metrics": ["Headcount", "Attendance Rate (%)", "Overtime Share (%)", "Attrition Rate (%)", "Total Payroll Cost (INR)", "Avg Salary (INR)"],
        "levels": ["Company", "Department", "Team"],
        "extra_dims": ["None", "Location", "Grade"],
        "scoped": False,
    },
    "HR": {
        "metrics": ["Headcount", "Attendance Rate (%)", "Overtime Share (%)", "Attrition Rate (%)", "Total Payroll Cost (INR)", "Avg Salary (INR)"],
        "levels": ["Company", "Department", "Team"],
        "extra_dims": ["None", "Location", "Grade"],
        "scoped": False,
    },
    "EXECUTIVE": {
        "metrics": ["Headcount", "Attendance Rate (%)", "Overtime Share (%)", "Attrition Rate (%)", "Total Payroll Cost (INR)"],
        "levels": ["Company", "Department"],
        "extra_dims": ["None", "Location"],
        "scoped": False,
    },
    "MANAGER": {
        "metrics": ["Headcount", "Attendance Rate (%)", "Overtime Share (%)", "Attrition Rate (%)"],
        "levels": ["Department", "Team"],
        "extra_dims": ["None"],
        "scoped": True,
    },
}


@st.cache_data
def load_users():
    for p in USER_PATHS:
        if p.exists():
            return pd.read_csv(p)
    # Fallback demo users if file path differs
    return pd.DataFrame([
        {"user_id": "U01", "name": "Aarav (Admin)", "role": "ADMIN", "department_id": "ALL", "team_id": "ALL"},
        {"user_id": "U02", "name": "Priya (HR)", "role": "HR", "department_id": "ALL", "team_id": "ALL"},
        {"user_id": "U03", "name": "Vikram (Exec)", "role": "EXECUTIVE", "department_id": "ALL", "team_id": "ALL"},
        {"user_id": "U04", "name": "Karthik (Mgr - Eng)", "role": "MANAGER", "department_id": "DEPT-01", "team_id": "ALL"},
    ])


@st.cache_data
def load_data():
    con = duckdb.connect(DB_PATH, read_only=True)
    tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]

    emp = con.execute("SELECT * FROM dim_employee").df() if "dim_employee" in tables else pd.read_excel(EXCEL_PATH, sheet_name="dim_employee")
    dept = con.execute("SELECT * FROM dim_department").df() if "dim_department" in tables else pd.read_excel(EXCEL_PATH, sheet_name="dim_department")
    pay = con.execute("SELECT * FROM fact_payroll").df() if "fact_payroll" in tables else pd.read_excel(EXCEL_PATH, sheet_name="fact_payroll")
    att = con.execute("SELECT * FROM fact_attendance_monthly").df() if "fact_attendance_monthly" in tables else pd.read_excel(EXCEL_PATH, sheet_name="fact_attendance_monthly")
    con.close()

    # Clean known planted non-standard IDs
    if "payroll_item_id" in pay.columns:
        pay = pay[pay["payroll_item_id"].astype(str).str.match(r"^PI-\d{6}$")]
    if "attendance_fact_id" in att.columns:
        att = att[att["attendance_fact_id"].astype(str).str.match(r"^FA-\d{5}$")]

    # Latest month snapshots for clean aggregation
    pay["month"] = pd.to_datetime(pay["period_end_date"]).dt.to_period("M")
    latest_pay_m = pay["month"].max()
    pay_latest = pay[pay["month"] == latest_pay_m].groupby("employee_id", as_index=False).agg(
        employer_cost=("employer_cost", "sum"),
        overtime_pay=("overtime_pay", "sum"),
    )

    att["month"] = pd.to_datetime(att["period_end_date"]).dt.to_period("M")
    latest_att_m = att["month"].max()
    att_latest = att[att["month"] == latest_att_m].groupby("employee_id", as_index=False).agg(
        overtime_hours=("overtime_hours", "sum"),
        paid_leave_days=("paid_leave_days", "sum"),
        unpaid_absence_days=("unpaid_absence_days", "sum"),
    )

    df = emp.merge(dept[["department_id", "department_name"]], on="department_id", how="left")
    df = df.merge(pay_latest, on="employee_id", how="left")
    df = df.merge(att_latest, on="employee_id", how="left")

    # Standardize optional columns
    if "team_name" not in df.columns:
        df["team_name"] = df["team_id"].fillna("Unassigned") if "team_id" in df.columns else "General Team"
    if "location" not in df.columns:
        df["location"] = df["work_location"] if "work_location" in df.columns else "HQ"
    if "grade" not in df.columns:
        df["grade"] = df["job_level"] if "job_level" in df.columns else "Standard"

    df["is_exited"] = df["employment_status"].astype(str).str.upper().isin(["TERMINATED", "EXITED", "RESIGNED", "INACTIVE"]).astype(int) if "employment_status" in df.columns else 0
    df["att_rate"] = (1 - (df["unpaid_absence_days"].fillna(0) / 22.0)).clip(0, 1) * 100
    df["ot_share"] = (df["overtime_pay"].fillna(0) / df["employer_cost"].replace(0, pd.NA)).fillna(0) * 100

    return df


users_df = load_users()
df = load_data()

# --- SIDEBAR: ROLE & DRILL-DOWN CONTROLS ---
st.sidebar.header("1. Simulated User Login")
user_col = "name" if "name" in users_df.columns else users_df.columns[0]
selected_user_name = st.sidebar.selectbox("Select User", users_df[user_col].tolist())
user_row = users_df[users_df[user_col] == selected_user_name].iloc[0]

role = str(user_row.get("role", "MANAGER")).upper()
if role not in ROLE_PERMISSIONS:
    role = "MANAGER"
perms = ROLE_PERMISSIONS[role]

st.sidebar.info(f"**Role:** {role}  \n**Min Group Size:** {MIN_GROUP_SIZE} employees")

# Apply Role Scope Filtering (Managers only see their assigned department)
scoped_df = df.copy()
if perms["scoped"]:
    user_dept = str(user_row.get("department_id", ""))
    if user_dept and user_dept != "ALL":
        scoped_df = scoped_df[scoped_df["department_id"].astype(str) == user_dept]
    user_team = str(user_row.get("team_id", ""))
    if user_team and user_team not in ("", "ALL", "nan", "None"):
        scoped_df = scoped_df[scoped_df["team_id"].astype(str) == user_team]

st.sidebar.header("2. Explore Controls")
metric = st.sidebar.selectbox("Metric", perms["metrics"])
drill_level = st.sidebar.radio("Drill-Down Level", perms["levels"])

selected_dept = "All"
if drill_level in ["Department", "Team"] and not perms["scoped"]:
    depts = ["All"] + sorted(scoped_df["department_name"].dropna().unique().tolist())
    selected_dept = st.sidebar.selectbox("Filter Department", depts)
    if selected_dept != "All":
        scoped_df = scoped_df[scoped_df["department_name"] == selected_dept]

extra_dim = st.sidebar.selectbox("Secondary Breakdown", perms["extra_dims"])

# --- MAIN VIEW ---
st.title("Self-Service KPI Explorer")
st.caption(f"Logged in as **{selected_user_name}** (`{role}`) • Privacy threshold: **{MIN_GROUP_SIZE} people minimum per group**")

# Determine grouping columns
group_cols = []
if drill_level == "Company":
    scoped_df["Company"] = "Zenith Nova Technologies"
    group_cols = ["Company"]
elif drill_level == "Department":
    group_cols = ["department_name"]
elif drill_level == "Team":
    group_cols = ["department_name", "team_name"]

if extra_dim != "None":
    dim_map = {"Location": "location", "Grade": "grade"}
    group_cols.append(dim_map[extra_dim])

# Aggregate metrics
agg_df = scoped_df.groupby(group_cols, dropna=False).agg(
    group_size=("employee_id", "nunique"),
    exits=("is_exited", "sum"),
    att_rate=("att_rate", "mean"),
    ot_share=("ot_share", "mean"),
    total_pay=("employer_cost", "sum"),
    avg_pay=("employer_cost", "mean"),
).reset_index()

agg_df["Headcount"] = agg_df["group_size"]
agg_df["Attrition Rate (%)"] = (agg_df["exits"] / agg_df["group_size"] * 100).round(2)
agg_df["Attendance Rate (%)"] = agg_df["att_rate"].round(2)
agg_df["Overtime Share (%)"] = agg_df["ot_share"].round(2)
agg_df["Total Payroll Cost (INR)"] = agg_df["total_pay"].round(0)
agg_df["Avg Salary (INR)"] = agg_df["avg_pay"].round(0)

# --- PRIVACY ENFORCEMENT (k-ANONYMITY + COMPLEMENTARY SUPPRESSION) ---
small_mask = agg_df["group_size"] < MIN_GROUP_SIZE
suppressed_count = int(small_mask.sum())

# Complementary suppression: if exactly 1 group is hidden, hide the next smallest group
# so a user cannot subtract visible groups from the parent total to deduce the hidden group.
if suppressed_count == 1 and len(agg_df) > 1:
    valid_indices = agg_df[~small_mask].sort_values("group_size").index
    if len(valid_indices) > 0:
        small_mask.loc[valid_indices[0]] = True
        suppressed_count += 1

safe_df = agg_df[~small_mask].copy()

if suppressed_count > 0:
    st.warning(
        f"🔒 **Privacy Protection Active:** {suppressed_count} group(s) with fewer than "
        f"{MIN_GROUP_SIZE} employees (or required for complementary suppression) have been hidden "
        f"to prevent individual identification."
    )

if safe_df.empty:
    st.error("No groups meet the minimum privacy threshold of 5 employees for this filter combination. Broaden your drill-down or remove the secondary breakdown.")
else:
    x_axis = group_cols[-1]
    color_col = group_cols[0] if len(group_cols) > 1 else None
    fig = px.bar(
        safe_df,
        x=x_axis,
        y=metric,
        color=color_col,
        barmode="group",
        title=f"{metric} by {' → '.join(group_cols)}",
    )
    st.plotly_chart(fig, use_container_width=True)

    display_cols = group_cols + ["Headcount", metric] if metric != "Headcount" else group_cols + ["Headcount"]
    st.dataframe(safe_df[display_cols], hide_index=True, use_container_width=True)