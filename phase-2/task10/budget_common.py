import duckdb

DB = "pulseiq.duckdb"
NUMERIC = ("TINYINT", "SMALLINT", "INTEGER", "INT", "BIGINT", "HUGEINT", "DOUBLE", "FLOAT", "REAL", "DECIMAL")


def connect(read_only=True):
    return duckdb.connect(DB, read_only=read_only)


def table_cols(con, table):
    df = con.sql(f"DESCRIBE {table}").df()
    return dict(zip(df["column_name"], df["column_type"]))


def is_numeric(t):
    return t.upper().startswith(NUMERIC)


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


def where_is(con, name, schemas=("dw", "clean", "raw", "main")):
    for s in schemas:
        n = con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
                        [s, name]).fetchone()[0]
        if n:
            return s
    return None


def month_sql(col, ctype, alias):
    """SQL that turns a month/date column into text like 2025-04."""
    q = f'{alias}."{col}"'
    t = ctype.upper()
    if t.startswith("DATE") or t.startswith("TIMESTAMP"):
        return f"strftime(CAST({q} AS DATE), '%Y-%m')"
    if t.startswith(NUMERIC):
        s = f"CAST({q} AS VARCHAR)"
        return (f"CASE WHEN length({s}) >= 8 THEN strftime(TRY_STRPTIME(substr({s}, 1, 8), '%Y%m%d'), '%Y-%m') "
                f"ELSE substr({s}, 1, 4) || '-' || substr({s}, 5, 2) END")
    return f"substr(CAST({q} AS VARCHAR), 1, 7)"