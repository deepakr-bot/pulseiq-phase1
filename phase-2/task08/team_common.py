import duckdb

DB = "pulseiq.duckdb"


def connect(read_only=True):
    return duckdb.connect(DB, read_only=read_only)


def table_cols(con, table):
    df = con.sql(f"DESCRIBE {table}").df()
    return dict(zip(df["column_name"], df["column_type"]))


def find(columns, *wanted):
    """Exact match first, then 'contains'. Returns the real column name or None."""
    low = {c.lower(): c for c in columns}
    for w in wanted:
        if w in low:
            return low[w]
    for w in wanted:
        for lc, c in low.items():
            if w in lc:
                return c
    return None


def detect(con):
    ft = table_cols(con, "dw.fact_task")
    tm = table_cols(con, "dw.dim_team")
    sp = table_cols(con, "dw.dim_sprint")
    m = {
        "task_id": find(ft, "task_id", "task_key"),
        "team": find(ft, "team_id", "team_key", "team"),
        "sprint": find(ft, "sprint_id", "sprint_key", "sprint"),
        "status": find(ft, "status", "task_status", "state"),
        "points": find(ft, "story_points", "points", "estimate"),
        "created": find(ft, "created_date", "created_at", "created_on", "created"),
        "started": find(ft, "started_date", "start_date", "started_at", "started", "in_progress"),
        "done": find(ft, "completed_date", "done_date", "resolved_date", "closed_date",
                     "completed_at", "completed", "resolved", "closed"),
        "due": find(ft, "due_date", "due", "deadline", "planned_end"),
        "reopened": find(ft, "reopened_flag", "is_reopened", "reopen_count", "reopened_count",
                         "reopened", "reopen"),
        "blocked": find(ft, "blocked_flag", "is_blocked", "blocked_days", "blocked_count",
                        "blocked", "block"),
        "team_dim_id": find(tm, "team_id", "team_key"),
        "team_name": find(tm, "team_name", "name"),
        "sprint_dim_id": find(sp, "sprint_id", "sprint_key"),
        "sprint_name": find(sp, "sprint_name", "name", "label"),
        "sprint_start": find(sp, "start_date", "sprint_start", "start"),
    }
    if m["team_dim_id"] is None and m["team"] in tm:
        m["team_dim_id"] = m["team"]
    if m["sprint_dim_id"] is None and m["sprint"] in sp:
        m["sprint_dim_id"] = m["sprint"]
    return m, {"ft": ft, "tm": tm, "sp": sp}


def date_sql(col, ctype, alias):
    if col is None:
        return "CAST(NULL AS DATE)"
    q = f'{alias}."{col}"'
    if ctype.upper() in ("BIGINT", "INTEGER", "INT", "HUGEINT", "SMALLINT"):
        return f"CAST(TRY_STRPTIME(CAST({q} AS VARCHAR), '%Y%m%d') AS DATE)"
    return f"TRY_CAST({q} AS DATE)"


def flag_sql(col, ctype, alias):
    if col is None:
        return "0"
    q = f'{alias}."{col}"'
    if ctype.upper() == "VARCHAR":
        return (f"(CASE WHEN {q} IS NULL OR TRIM({q}) = '' "
                f"OR UPPER(TRIM({q})) IN ('N','NO','FALSE','F','0','NONE') THEN 0 ELSE 1 END)")
    return f"(CASE WHEN COALESCE(CAST({q} AS DOUBLE), 0) > 0 THEN 1 ELSE 0 END)"