# main.py
from pathlib import Path
from datetime import datetime, timezone

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# main.py is in phase-4/task19, so parents[2] is the repo root where pulseiq.duckdb lives
DB_PATH = Path(__file__).resolve().parents[2] / "pulseiq.duckdb"

app = FastAPI(
    title="PulseIQ Metrics API",
    description="Trusted company metrics with definitions, lineage and freshness.",
    version="1.0.0",
)

# Lets a browser-based dashboard call this API. Replace "*" with your dashboard domain when deployed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Five metrics. Each entry holds the definition, source, lineage and the SQL that produces the value.
METRICS = {
    "active_headcount": {
        "name": "Active Headcount",
        "definition": "Total employees in the latest month, summed across all departments.",
        "source_table": "m01_headcount (from fact_headcount_monthly)",
        "lineage": (
            "HR Raw Feed -> ETL Pipeline -> fact_headcount_monthly "
            "-> m01_headcount -> Metrics API -> Executive Dashboard"
        ),
        "query": (
            "SELECT SUM(headcount) FROM m01_headcount "
            "WHERE month = (SELECT MAX(month) FROM m01_headcount)"
        ),
    },
    "total_teams": {
        "name": "Total Active Teams",
        "definition": "Number of teams with sprint records in the task system.",
        "source_table": "v_team_overall (from fact_task)",
        "lineage": (
            "Task Tracker Raw Feed -> ETL Pipeline -> fact_task "
            "-> v_team_overall -> Metrics API -> Executive Dashboard"
        ),
        "query": "SELECT COUNT(*) FROM dw.v_team_overall",
    },
    "total_payroll_expense": {
        "name": "Total Payroll Expense (Employer Cost)",
        "definition": "Total employer cost for the latest pay month, all departments.",
        "source_table": "v_payroll_company_month (from fact_payroll)",
        "lineage": (
            "Payroll Raw Feed -> ETL Pipeline -> fact_payroll "
            "-> v_payroll_company_month -> Metrics API -> Executive Dashboard"
        ),
        "query": (
    "SELECT ROUND(employer_cost, 2) FROM dw.v_payroll_company_month "
    "ORDER BY month_end DESC LIMIT 1"
        ),
    },
    "attrition_12m": {
        "name": "Company Attrition (Rolling 12 Months)",
        "definition": "Percentage of employees who exited over the rolling 12 months, latest month.",
        "source_table": "v5_company_attrition_12m (from fact_headcount_monthly)",
        "lineage": (
            "HR Raw Feed -> ETL Pipeline -> fact_headcount_monthly "
            "-> v5_company_attrition_12m -> Metrics API -> Executive Dashboard"
        ),
        "query": (
            "SELECT attrition_12m_pct FROM v5_company_attrition_12m "
            "ORDER BY month DESC LIMIT 1"
        ),
    },
    "on_time_delivery_rate": {
        "name": "On-Time Delivery Rate",
        "definition": "Share of tasks with a due date that were completed on time, all teams.",
        "source_table": "v_team_overall (from fact_task)",
        "lineage": (
            "Task Tracker Raw Feed -> ETL Pipeline -> fact_task "
            "-> v_team_overall -> Metrics API -> Executive Dashboard"
        ),
        "query": (
            "SELECT ROUND(SUM(on_time_done) * 100.0 / NULLIF(SUM(due_done), 0), 1) "
            "FROM dw.v_team_overall"
        ),
    },
}


def fetch_value(query: str):
    """Run a read-only query against the warehouse and return the first value."""
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        row = con.execute(query).fetchone()
        return row[0] if row else None
    finally:
        con.close()


def get_last_refresh() -> str:
    """Freshness = latest ETL run finish time. Falls back to the DB file's modified time."""
    try:
        value = fetch_value("SELECT MAX(finished_at) FROM etl_run_log")
        if value is not None:
            return value.strftime("%Y-%m-%d %H:%M:%S") + " UTC"
    except duckdb.Error:
        pass
    ts = DB_PATH.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def freshness_statement() -> str:
    return f"Data refreshed at {get_last_refresh()}."


@app.get("/")
def root():
    return {"message": "PulseIQ Metrics API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def list_metrics():
    return {
        "status": "success",
        "freshness_statement": freshness_statement(),
        "metrics": [{"metric_id": k, "name": v["name"]} for k, v in METRICS.items()],
    }


@app.get("/metrics/{metric_id}")
def get_metric(metric_id: str):
    m = METRICS.get(metric_id)
    if not m:
        raise HTTPException(status_code=404, detail=f"Unknown metric: {metric_id}")
    try:
        value = fetch_value(m["query"])
    except duckdb.Error as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    return {
        "metric_id": metric_id,
        "name": m["name"],
        "value": value,
        "definition": m["definition"],
        "source_table": m["source_table"],
        "lineage": m["lineage"],
        "last_refresh": get_last_refresh(),
        "freshness_statement": freshness_statement(),
    }