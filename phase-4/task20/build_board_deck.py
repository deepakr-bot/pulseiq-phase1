# scripts/build_board_deck.py
"""Build a 9-slide board deck from the live warehouse.
Run quality_checks.py first. Then, from the repo root:  python scripts/build_board_deck.py
Output: reports/board_deck.pptx
"""
from datetime import datetime
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches, Pt

from quality_checks import DB_PATH, REPORT, ROOT, tbl

CHARTS = ROOT / "reports" / "charts"
OUT = ROOT / "reports" / "board_deck.pptx"
BLUE = "#1f4e79"


def q(con, sql):
    return con.execute(sql).fetchall()


def chart(x, y, title, ylabel, name, kind="line"):
    CHARTS.mkdir(parents=True, exist_ok=True)
    path = CHARTS / f"{name}.png"
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if kind == "bar":
        ax.bar([str(v) for v in x], y, color=BLUE)
        ax.tick_params(axis="x", rotation=45)
    else:
        ax.plot(x, y, marker="o", color=BLUE)
        fig.autofmt_xdate()
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def build_findings(con):
    hc = tbl(con, "m01_headcount")
    att = tbl(con, "v5_company_attrition_12m")
    pay = tbl(con, "v_payroll_company_month")
    dso = tbl(con, "m20_dso")
    teams = tbl(con, "v_team_overall")

    hc_s = q(con, f"SELECT month, SUM(headcount) FROM {hc} GROUP BY month ORDER BY month")
    att_s = q(con, f"SELECT month, attrition_12m_pct FROM {att} ORDER BY month")
    pay_s = q(con, f"SELECT month_end, employer_cost FROM {pay} ORDER BY month_end")
    dso_s = q(con, f"SELECT month_end, dso_days FROM {dso} ORDER BY month_end")
    team_s = q(con, f"SELECT team, ROUND(on_time_done*100.0/NULLIF(due_done,0),1) "
                    f"FROM {teams} ORDER BY 2 DESC")
    ot_now = q(con, f"SELECT ROUND(SUM(on_time_done)*100.0/NULLIF(SUM(due_done),0),1) FROM {teams}")[0][0]

    # Review each recommendation against its chart before presenting. Edit the wording if the trend says otherwise.
    return [
        {
            "headline": f"Headcount is {hc_s[-1][1]:,.0f} across departments",
            "evidence": "Total headcount by month, summed across departments.",
            "recommendation": "Tie new hiring to this trend and review it monthly before approving roles.",
            "chart": chart([r[0] for r in hc_s], [r[1] for r in hc_s],
                           "Headcount by month", "Employees", "people"),
        },
        {
            "headline": f"Rolling 12-month attrition is {att_s[-1][1]:.1f}%",
            "evidence": "Share of employees who exited over the rolling 12 months.",
            "recommendation": "Review exit reasons in the departments with the most exits before the next hiring round.",
            "chart": chart([r[0] for r in att_s], [r[1] for r in att_s],
                           "Rolling 12-month attrition", "Percent", "attrition"),
        },
        {
            "headline": f"Latest employer cost is {pay_s[-1][1]:,.0f}",
            "evidence": "Employer cost for the latest pay month, all departments.",
            "recommendation": "Compare cost per head against headcount each month before approving budget increases.",
            "chart": chart([r[0] for r in pay_s], [r[1] for r in pay_s],
                           "Employer cost by month", "Amount", "payroll"),
        },
        {
            "headline": f"Days sales outstanding is {dso_s[-1][1]:.0f} days",
            "evidence": "How long it takes to collect receivables, by month.",
            "recommendation": "Set a collection target and review overdue invoices every week.",
            "chart": chart([r[0] for r in dso_s], [r[1] for r in dso_s],
                           "Days sales outstanding", "Days", "cash"),
        },
        {
            "headline": f"On-time delivery is {ot_now}% across teams",
            "evidence": "Share of tasks with a due date completed on time, by team.",
            "recommendation": "Start with the teams at the bottom of this chart and review their late tasks first.",
            "chart": chart([r[0] for r in team_s], [r[1] or 0 for r in team_s],
                           "On-time delivery by team (%)", "Percent", "teams", kind="bar"),
        },
    ]


def add_text(slide, left, top, width, height, lines):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, (text, bold, size) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text
        p.font.bold = bold
        p.font.size = Pt(size)


def new_slide(prs, title):
    s = prs.slides.add_slide(prs.slide_layouts[5])
    t = s.shapes.title
    t.text = title
    t.left, t.top, t.width, t.height = Inches(0.5), Inches(0.3), Inches(12.3), Inches(1.1)
    t.text_frame.paragraphs[0].font.size = Pt(28)
    return s


def main():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        findings = build_findings(con)
        last_etl = con.execute(f"SELECT MAX(finished_at) FROM {tbl(con, 'etl_run_log')}").fetchone()[0]
    finally:
        con.close()

    days_old = (datetime.now() - last_etl).days if last_etl else None
    stamp = f"{last_etl:%d %b %Y}" if last_etl else "unknown date"
    fails = None
    if REPORT.exists():
        fails = [l for l in REPORT.read_text(encoding="utf-8").splitlines() if "| FAIL |" in l]

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    # 1. Cover
    s = prs.slides.add_slide(prs.slide_layouts[0])
    s.shapes.title.text = "PulseIQ: Board Pack"
    s.placeholders[1].text = f"Company metrics, data last refreshed {stamp}"

    # 2. Summary
    s = new_slide(prs, "Five findings for the board")
    add_text(s, Inches(0.7), Inches(1.6), Inches(12), Inches(5),
             [(f"{i}. {f['headline']}", False, 22) for i, f in enumerate(findings, 1)])

    # 3-7. One finding per slide
    for i, f in enumerate(findings, 1):
        s = new_slide(prs, f"{i}. {f['headline']}")
        s.shapes.add_picture(str(f["chart"]), Inches(0.5), Inches(1.6), width=Inches(7.2))
        add_text(s, Inches(8.0), Inches(1.7), Inches(4.9), Inches(5), [
            ("Evidence", True, 18), (f["evidence"], False, 16),
            ("Recommendation", True, 18), (f["recommendation"], False, 16),
        ])

    # 8. What we are not recommending yet
    s = new_slide(prs, "What we are not recommending yet")
    stale = (f"The last ETL refresh was {days_old} days ago, so trends may not reflect current conditions."
             if days_old is not None else "The last ETL refresh time could not be read.")
    add_text(s, Inches(0.7), Inches(1.6), Inches(12), Inches(5), [
        ("We will not recommend changing the hiring freeze or the payroll budget yet.", False, 22),
        (stale, False, 20),
        ("A budget decision now would rest on old data. We will bring this back after a confirmed refresh.", False, 20),
    ])

    # 9. Data quality
    s = new_slide(prs, "Data quality and reconciliation")
    if fails is None:
        msg = "No quality report found. Run scripts/quality_checks.py first."
    elif fails:
        msg = (f"{len(fails)} check(s) failed. See reports/quality_report.md, "
               "and disclose them before the board relies on these numbers.")
    else:
        msg = "All quality and reconciliation checks passed on the live data."
    add_text(s, Inches(0.7), Inches(1.6), Inches(12), Inches(5), [(msg, False, 22)])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT))
    print(f"Saved {OUT} with {len(prs.slides)} slides")


if __name__ == "__main__":
    main()