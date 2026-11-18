# scripts/quality_checks.py
"""Re-run reconciliations and data quality checks on the live warehouse.
Run from the repo root:  python scripts/quality_checks.py
Writes reports/quality_report.md. Exits with code 1 if any check fails.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "pulseiq.duckdb"
REPORT = ROOT / "reports" / "quality_report.md"

results = []  # (name, passed, detail)


def tbl(con, name):
    """Return schema-qualified name, e.g. dw.v_team_overall, whichever schema holds it."""
    row = con.execute(
        "SELECT table_schema FROM information_schema.tables WHERE table_name = ? ORDER BY table_schema",
        [name],
    ).fetchone()
    if not row:
        raise RuntimeError(f"Table or view not found: {name}")
    return f"{row[0]}.{name}"


def check(name, passed, detail):
    results.append((name, bool(passed), detail))


def run(con):
    last_etl = con.execute(f"SELECT MAX(finished_at) FROM {tbl(con, 'etl_run_log')}").fetchone()[0]
    age = (datetime.now() - last_etl).days if last_etl else None
    check("ETL freshness: last run within 7 days", age is not None and age <= 7,
          f"last finished {last_etl}, {age} days ago")

    rows = con.execute(
        f"SELECT table_name, rows_in, rows_passed, rows_quarantined FROM {tbl(con, 'etl_summary')}"
    ).fetchall()
    bad = [r[0] for r in rows if r[1] != (r[2] or 0) + (r[3] or 0)]
    check("ETL row balance: in = passed + quarantined", not bad,
          f"{len(rows)} tables checked; mismatches: {bad or 'none'}")

    hc = tbl(con, "m01_headcount")
    fh = tbl(con, "fact_headcount_monthly")
    view_hc = con.execute(f"SELECT SUM(headcount) FROM {hc} WHERE month = (SELECT MAX(month) FROM {hc})").fetchone()[0]
    fact_hc = con.execute(
        f"SELECT SUM(headcount_end) FROM {fh} WHERE month_start_date = (SELECT MAX(month_start_date) FROM {fh})"
    ).fetchone()[0]
    check("Reconcile headcount: metric view = fact table (latest month)", view_hc == fact_hc,
          f"view={view_hc}, fact={fact_hc}")

    pv = tbl(con, "v_payroll_company_month")
    fp = tbl(con, "fact_payroll")
    view_cost = con.execute(f"SELECT employer_cost FROM {pv} ORDER BY month_end DESC LIMIT 1").fetchone()[0]
    latest_end = con.execute(f"SELECT MAX(period_end_date) FROM {fp}").fetchone()[0]
    fact_cost = con.execute(
        f"SELECT SUM(employer_cost) FROM {fp} WHERE period_end_date = ?", [latest_end]
    ).fetchone()[0]
    check("Reconcile payroll: cost view = fact table (latest period)",
          abs((view_cost or 0) - (fact_cost or 0)) < 1,
          f"view={view_cost}, fact={fact_cost} (a difference may be expected if rows are excluded)")

    att = tbl(con, "v5_company_attrition_12m")
    out = con.execute(f"SELECT COUNT(*) FROM {att} WHERE attrition_12m_pct < 0 OR attrition_12m_pct > 100").fetchone()[0]
    check("Range: attrition between 0 and 100", out == 0, f"{out} out-of-range rows")

    teams = tbl(con, "v_team_overall")
    over = con.execute(f"SELECT COUNT(*) FROM {teams} WHERE on_time_done > due_done").fetchone()[0]
    check("Logic: on-time tasks never exceed tasks with due dates", over == 0, f"{over} teams break the rule")

    q = con.execute(f"SELECT table_name, COUNT(*) FROM {tbl(con, 'quarantine')} GROUP BY 1").fetchall()
    check("Info: quarantined rows listed for review", True, f"by table: {q or 'none'}")


def write_report():
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Quality and reconciliation report",
        f"Run: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for name, ok, detail in results:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        run(con)
    finally:
        con.close()
    write_report()
    for name, ok, detail in results:
        print("PASS" if ok else "FAIL", "-", name, "-", detail)
    sys.exit(0 if all(ok for _, ok, _ in results) else 1)