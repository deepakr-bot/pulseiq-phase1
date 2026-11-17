import json
from pathlib import Path

import duckdb
import pandas as pd

HERE = Path(__file__).resolve().parent
DB = HERE.parents[1] / "phase-3" / "pulseiq.duckdb"
OUT = HERE / "data"
MIN_GROUP = 5  # never publish a department-month with fewer people than this


def month_key(s):
    return pd.to_datetime(s).dt.to_period("M").dt.to_timestamp()


def main():
    OUT.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    q = con.execute

    rev = q("SELECT month, SUM(revenue) AS revenue FROM m16_revenue GROUP BY month").df()
    m18 = q("SELECT month, net_profit, operating_margin_pct FROM m18_operating_margin").df()
    m20 = q("SELECT month_end AS month, dso_days FROM m20_dso").df()
    hc = q("SELECT department_id, month, headcount FROM m01_headcount").df()
    att = q("SELECT department_id, month_end AS month, attendance_rate FROM m13_attendance_rate").df()
    ot = q("SELECT department_id, month_end AS month, overtime_share_pct FROM m11_overtime_share").df()
    attr = q("SELECT department_id, month, attrition_rate_pct FROM m04_attrition_rate_monthly").df()
    dept = q("SELECT department_id, department_name FROM v5_department").df()
    cutoff = q("SELECT MAX(entry_date) FROM fact_ledger").fetchone()[0]
    con.close()

    # Company level: all departments, before any privacy filter
    for df in (rev, m18, m20):
        df["month"] = month_key(df["month"])
    company_hc = (hc.assign(month=month_key(hc["month"]))
                    .groupby("month")["headcount"].sum().reset_index())
    company = (rev.merge(m18, on="month", how="left")
                  .merge(m20, on="month", how="left")
                  .merge(company_hc, on="month", how="left")
                  .rename(columns={"net_profit": "net_profit_inr"}))
    company["month"] = company["month"].dt.strftime("%Y-%m")
    company.to_csv(OUT / "company_monthly.csv", index=False)

    # Department level: aggregates only, small groups hidden
    dept_df = hc.assign(month=month_key(hc["month"]))
    for df in (att, ot, attr):
        df["month"] = month_key(df["month"])
    dept_df = (dept_df.merge(att, on=["department_id", "month"], how="left")
                      .merge(ot, on=["department_id", "month"], how="left")
                      .merge(attr, on=["department_id", "month"], how="left")
                      .merge(dept, on="department_id", how="left"))
    dept_df = dept_df[dept_df["headcount"] >= MIN_GROUP].copy()
    dept_df["month"] = dept_df["month"].dt.strftime("%Y-%m")
    dept_df.to_csv(OUT / "department_monthly.csv", index=False)

    meta = {
        "data_cutoff": str(pd.Timestamp(cutoff).date()),
        "min_group_size": MIN_GROUP,
        "company_months": len(company),
        "department_rows": len(dept_df),
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()