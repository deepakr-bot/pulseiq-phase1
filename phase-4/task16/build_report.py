import argparse
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_DB = REPO / "phase-3" / "pulseiq.duckdb"
OUT_DIR = HERE / "output"


def month_key(s):
    return pd.to_datetime(s).dt.to_period("M").dt.to_timestamp()


def load(db):
    con = duckdb.connect(str(db), read_only=True)
    data = {
        "m04": con.execute("SELECT department_id, month, attrition_rate_pct FROM m04_attrition_rate_monthly").df(),
        "m13": con.execute("SELECT department_id, month_end AS month, attendance_rate FROM m13_attendance_rate").df(),
        "m16": con.execute("SELECT month, SUM(revenue) AS revenue FROM m16_revenue GROUP BY month").df(),
        "m18": con.execute("SELECT month, net_profit, operating_margin_pct FROM m18_operating_margin").df(),
        "m20": con.execute("SELECT month_end AS month, dso_days FROM m20_dso").df(),
        "gl": con.execute("SELECT entry_date, account_code, debit, credit FROM fact_ledger").df(),
        "acc": con.execute("SELECT account_code, account_name, account_type, statement, is_group FROM dim_account").df(),
    }
    con.close()
    return data


def build_monthly(d):
    rev = d["m16"].assign(month=month_key(d["m16"]["month"])).set_index("month")["revenue"]
    m18 = d["m18"].assign(month=month_key(d["m18"]["month"])).set_index("month")
    dso = d["m20"].assign(month=month_key(d["m20"]["month"])).groupby("month")["dso_days"].mean()
    att = d["m13"].assign(month=month_key(d["m13"]["month"])).groupby("month")["attendance_rate"].mean()
    attr = d["m04"].assign(month=month_key(d["m04"]["month"])).groupby("month")["attrition_rate_pct"].mean()
    return pd.concat({
        "Revenue": rev,
        "Net profit": m18["net_profit"],
        "Operating margin %": m18["operating_margin_pct"],
        "DSO": dso,
        "Attendance rate": att,
        "Monthly attrition %": attr,
    }, axis=1, sort=True).sort_index()


def expense_by_category(d, month_start):
    acc = d["acc"]
    detail = acc[(acc["statement"] == "Profit & Loss") & (acc["is_group"] == "N")][
        ["account_code", "account_name", "account_type"]]
    gl = d["gl"].copy()
    gl["entry_date"] = pd.to_datetime(gl["entry_date"])
    x = gl.merge(detail, on="account_code")
    x = x[(x["account_type"] == "EXPENSE") &
          (x["entry_date"].dt.to_period("M").dt.to_timestamp() == month_start)]
    return (x.assign(amount=x["debit"] - x["credit"])
             .groupby("account_name")["amount"].sum()
             .sort_values(ascending=False))


def fmt(x, template):
    return "n/a" if pd.isna(x) else template.format(x)


def trend_chart(m, month_start, path):
    part = m.loc[:month_start].tail(12)
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.plot(part.index, part["Revenue"] / 1e6, marker="o", label="Revenue (M)")
    ax.plot(part.index, part["Net profit"] / 1e6, marker="o", label="Net profit (M)")
    ax.set_ylabel("INR millions")
    ax.set_title("Last 12 months up to the report month")
    ax.legend(loc="upper left")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def expense_chart(series, path):
    top = series.head(8)
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.barh(top.index[::-1], top.values[::-1] / 1e6)
    ax.set_xlabel("INR millions")
    ax.set_title("Top expense categories in the report month")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def build_pdf(month, start, end, cutoff, kpis, out_path, charts):
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"PulseIQ monthly report: {month}", styles["Title"]),
        Paragraph(f"Period covered: {start} to {end}", styles["Normal"]),
        Paragraph(f"Data cut-off (latest ledger date): {cutoff}", styles["Normal"]),
        Paragraph("Source: pulseiq.duckdb metric views and fact_ledger. Amounts in INR.", styles["Normal"]),
        Spacer(1, 6 * mm),
    ]
    rows = [["KPI", "Value"]] + [[k, v] for k, v in kpis]
    table = Table(rows, colWidths=[100 * mm, 60 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    story += [table, Spacer(1, 6 * mm)]
    story += [Image(charts[0], width=170 * mm, height=73 * mm), Spacer(1, 4 * mm)]
    if charts[1]:
        story += [Image(charts[1], width=170 * mm, height=85 * mm)]
    doc = SimpleDocTemplate(str(out_path), pagesize=A4,
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm)
    doc.build(story)


def main():
    parser = argparse.ArgumentParser(description="Build the monthly PulseIQ report pack")
    parser.add_argument("--month", required=True, help="Month to report, for example 2026-09")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to pulseiq.duckdb")
    args = parser.parse_args()

    month_start = pd.Timestamp(args.month + "-01")
    month_end = month_start + pd.offsets.MonthEnd(0)

    d = load(args.db)
    m = build_monthly(d)
    if month_start not in m.index:
        raise SystemExit(f"No data for {args.month} in the metric views.")
    cur = m.loc[month_start]
    cutoff = pd.to_datetime(d["gl"]["entry_date"]).max().date()

    kpis = [
        ("Revenue (excl. interest)", fmt(cur["Revenue"] / 1e6, "{:,.1f} M INR")),
        ("Operating margin", fmt(cur["Operating margin %"], "{:.1f} %")),
        ("Days sales outstanding", fmt(cur["DSO"], "{:.1f} days")),
        ("Attendance rate", fmt(cur["Attendance rate"] * 100, "{:.1f} %")),
        ("Monthly attrition", fmt(cur["Monthly attrition %"], "{:.2f} %")),
    ]

    OUT_DIR.mkdir(exist_ok=True)
    trend_png = OUT_DIR / f"trend_{args.month}.png"
    expense_png = OUT_DIR / f"expense_{args.month}.png"
    trend_chart(m, month_start, trend_png)

    exp = expense_by_category(d, month_start)
    if len(exp):
        expense_chart(exp, expense_png)
        expense_file = expense_png
    else:
        expense_file = None

    out_pdf = OUT_DIR / f"pulseiq_report_{args.month}.pdf"
    build_pdf(args.month, month_start.date(), month_end.date(), cutoff,
              kpis, out_pdf, (trend_png, expense_file))
    print(f"Report written: {out_pdf}")


if __name__ == "__main__":
    main()