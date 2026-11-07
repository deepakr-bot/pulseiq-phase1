import sys
import numpy as np
import pandas as pd
from team_common import connect, detect

pd.set_option("display.width", 200)
con = connect()
m, types = detect(con)
raw = con.sql("SELECT * FROM dw.fact_task").df()
tmd = con.sql("SELECT * FROM dw.dim_team").df()
over = con.sql("SELECT * FROM dw.v_team_overall").df().set_index("team")

names = dict(zip(tmd[m["team_dim_id"]].astype(str),
                 (tmd[m["team_name"]] if m["team_name"] else tmd[m["team_dim_id"]]).astype(str)))
raw["team_name"] = raw[m["team"]].astype(str).map(names).fillna(raw[m["team"]].astype(str))


def date_col(name):
    if name is None:
        return pd.Series(pd.NaT, index=raw.index)
    s = raw[name]
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_datetime(s.astype("Int64").astype(str), format="%Y%m%d", errors="coerce")
    return pd.to_datetime(s, errors="coerce")


def flag(name):
    if name is None:
        return pd.Series(False, index=raw.index)
    s = raw[name]
    if pd.api.types.is_bool_dtype(s):
        return s.fillna(False)
    if pd.api.types.is_numeric_dtype(s):
        return s.fillna(0) > 0
    t = s.astype(str).str.strip().str.upper()
    return ~(s.isna() | t.isin(["", "N", "NO", "FALSE", "F", "0", "NONE", "NAN"]))


st_up = raw[m["status"]].astype(str).str.upper()
cancelled = st_up.str.contains("CANCEL")
done = (~cancelled) & st_up.str.contains("DONE|COMPLET|CLOSED|RESOLV")
planned = ~cancelled
created, started, done_d, due = date_col(m["created"]), date_col(m["started"]), date_col(m["done"]), date_col(m["due"])
start = started.fillna(created)
points = pd.to_numeric(raw[m["points"]], errors="coerce").fillna(0) if m["points"] else pd.Series(1.0, index=raw.index)
reopened = flag(m["reopened"]) | st_up.str.contains("REOPEN")
blocked = flag(m["blocked"]) | st_up.str.contains("BLOCK")
cyc = (done_d - start).dt.days
cyc_ok = done & done_d.notna() & start.notna() & (cyc >= 0)
due_ok = done & done_d.notna() & due.notna()
on_time = due_ok & (done_d <= due)

if len(sys.argv) >= 3:
    picks = sys.argv[1:3]
else:
    size = raw[planned].groupby("team_name").size().sort_values(ascending=False)
    picks = [size.index[0], size.index[len(size) // 2]]
print("Teams checked:", picks)

rows = []
for team in picks:
    k = raw["team_name"] == team
    n_sprints = raw.loc[k & planned, m["sprint"]].nunique()
    by_hand = {
        "planned tasks": int((k & planned).sum()),
        "cancelled tasks": int((k & cancelled).sum()),
        "done tasks": int((k & done).sum()),
        "points done": float(points[k & done].sum()),
        "sprints with work": int(n_sprints),
        "avg cycle days": float(cyc[k & cyc_ok].mean()),
        "on-time %": float(on_time[k & due_ok].mean() * 100),
        "blocked tasks": int((k & planned & blocked).sum()),
        "reopened tasks": int((k & planned & reopened).sum()),
    }
    o = over.loc[team]
    from_view = {
        "planned tasks": o["planned"], "cancelled tasks": o["cancelled"], "done tasks": o["done"],
        "points done": o["points_done"], "sprints with work": o["sprints"],
        "avg cycle days": o["cycle_sum"] / o["cycle_n"] if o["cycle_n"] else np.nan,
        "on-time %": o["on_time_done"] / o["due_done"] * 100 if o["due_done"] else np.nan,
        "blocked tasks": o["blocked"], "reopened tasks": o["reopened"],
    }
    for metric, hand in by_hand.items():
        vw = from_view[metric]
        ok = (np.isnan(hand) and np.isnan(vw)) or abs(hand - vw) < 0.01
        rows.append({"team": team, "metric": metric, "by hand (raw rows)": round(hand, 2),
                     "metric view": round(float(vw), 2), "match": "YES" if ok else "NO"})

    cols = [c for c in [m["task_id"], m["sprint"], m["status"], m["points"], m["created"],
                        m["started"], m["done"], m["due"]] if c]
    safe = team.replace(" ", "_").replace("&", "and")
    raw.loc[k, cols].to_csv(f"reports/verify_rows_{safe}.csv", index=False)

out = pd.DataFrame(rows)
print(out.to_string(index=False))
out.to_csv("reports/verification_table.csv", index=False)
with open("reports/verification_table.md", "w", encoding="utf-8") as f:
    f.write("| team | metric | by hand (raw rows) | metric view | match |\n|---|---|---|---|---|\n")
    for r in rows:
        f.write(f"| {r['team']} | {r['metric']} | {r['by hand (raw rows)']} | {r['metric view']} | {r['match']} |\n")
print("\nSaved reports/verification_table.md and reports/verification_table.csv")
print("All match:", (out["match"] == "YES").all())