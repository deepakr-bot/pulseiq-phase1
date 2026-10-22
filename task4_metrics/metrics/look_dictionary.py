import duckdb
con = duckdb.connect("pulseiq.duckdb")

def one(sql, p=None):
    return con.execute(sql, p or []).fetchone()

# M04 attrition monthly
d, m, v = one("SELECT department_id, month, attrition_rate_pct FROM m04_attrition_rate_monthly ORDER BY 1,2 LIMIT 1")
ex, hs = one("SELECT exits, headcount_start FROM dw.fact_headcount_monthly WHERE department_id=? AND month_start_date=?", [d, m])
print("M04 attrition monthly | dept", d, "| month", m)
print("   view says:", v, "| raw: exits =", ex, ", start headcount =", hs, "| calculator: exits / start x 100")

# M09 payroll cost (smallest allowed group, so the sum is short)
d, m, n = one("SELECT department_id, CAST(period_end_date AS DATE), COUNT(DISTINCT employee_id) AS n FROM dw.fact_payroll GROUP BY 1,2 HAVING COUNT(DISTINCT employee_id) >= 5 ORDER BY n, 1, 2 LIMIT 1")
v = one("SELECT payroll_cost FROM m09_payroll_cost WHERE department_id=? AND month_end=?", [d, m])[0]
costs = [r[0] for r in con.execute("SELECT employer_cost FROM dw.fact_payroll WHERE department_id=? AND CAST(period_end_date AS DATE)=?", [d, m]).fetchall()]
print("\nM09 payroll cost | dept", d, "| month end", m)
print("   view says:", round(v, 2), "| raw employer costs:", costs, "| calculator: add them up")

# M13 attendance rate
d, m, v = one("SELECT department_id, month_end, attendance_rate FROM m13_attendance_rate ORDER BY 1,2 LIMIT 1")
p, h, s = one("SELECT SUM(present_days), SUM(half_days_unpaid), SUM(scheduled_days) FROM dw.fact_attendance_monthly WHERE department_id=? AND CAST(period_end_date AS DATE)=?", [d, m])
print("\nM13 attendance rate | dept", d, "| month end", m)
print("   view says:", v, "| raw: present =", p, ", half days =", h, ", scheduled =", s, "| calculator: (present + 0.5 x half) / scheduled")

# M22 task completion
t, sp, v = one("SELECT team_id, sprint_id, completion_rate FROM m22_task_completion_rate ORDER BY 1,2 LIMIT 1")
done, notc = one("SELECT COUNT(*) FILTER (WHERE status='Done'), COUNT(*) FILTER (WHERE status<>'Cancelled') FROM dw.fact_task WHERE team_id=? AND sprint_id=?", [t, sp])
print("\nM22 task completion | team", t, "| sprint", sp)
print("   view says:", v, "| raw: done =", done, ", not cancelled =", notc, "| calculator: done / not cancelled")

# M24 velocity
t, sp, v = one("SELECT team_id, sprint_id, velocity FROM m24_velocity ORDER BY 1,2 LIMIT 1")
pts = [r[0] for r in con.execute("SELECT story_points FROM dw.fact_task WHERE status='Done' AND team_id=? AND sprint_id=?", [t, sp]).fetchall()]
print("\nM24 velocity | team", t, "| sprint", sp)
print("   view says:", v, "| raw story points of Done tasks:", pts, "| calculator: add them up")

