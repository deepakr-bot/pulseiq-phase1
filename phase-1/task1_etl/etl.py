import duckdb, re

DB = "pulseiq.duckdb"
NOT_ENFORCED = []

def sq(s):
    return s.replace("'", "''")

def sql_type(t):
    t = t.lower().strip()
    if t in ("string", "char(1)"): return None
    return {"int": "BIGINT", "date": "DATE", "timestamp": "TIMESTAMP",
            "decimal": "DECIMAL(18,4)"}.get(t, t.upper())

def dim_key(con, dim, col):
    cols = [r[0] for r in con.execute(f"DESCRIBE raw.{dim}").fetchall()]
    if col in cols:
        return col
    ids = [c for c in cols if c.endswith("_id") and col.endswith(c)]
    if ids:
        return max(ids, key=len)      # assignee_employee_id -> employee_id
    ids = [c for c in cols if c.endswith("_id")]
    return ids[0] if ids else cols[0]

def exists_check(q, k, dim):
    return (f"{q} IS NOT NULL AND CAST({q} AS VARCHAR) NOT IN "
            f"(SELECT CAST(\"{k}\" AS VARCHAR) FROM raw.{dim} WHERE \"{k}\" IS NOT NULL)")

def build_checks(con, table, col, dtype, nullable, rule, actual, all_tables):
    """Return list of (condition_meaning_BAD, reason)."""
    q = f'"{col}"'
    num = lambda c: f'TRY_CAST("{c}" AS DOUBLE)'
    dat = lambda c: f'TRY_CAST("{c}" AS DATE)'
    checks = []

    if nullable is False:
        checks.append((f"{q} IS NULL", f"{col}: empty but contract says required"))
    st = sql_type(dtype or "string")
    if st:
        checks.append((f"{q} IS NOT NULL AND TRY_CAST(CAST({q} AS VARCHAR) AS {st}) IS NULL",
                       f"{col}: not a valid {dtype}"))

    r = (rule or "").strip()
    low = r.lower()
    why = f"{col}: {r}"

    if not r or low in ("text", "utc", "plain english"):
        pass
    elif low == "semantic version text":
        checks.append((f"{q} IS NOT NULL AND NOT regexp_matches(CAST({q} AS VARCHAR), '\\d+\\.\\d+(\\.\\d+)?$')", why))
    elif low == "dept id or all":
        dim = "dim_department"
        if dim in all_tables:
            k = dim_key(con, dim, col)
            checks.append((f"{q} IS NOT NULL AND CAST({q} AS VARCHAR) <> 'ALL' AND CAST({q} AS VARCHAR) NOT IN "
                           f"(SELECT CAST(\"{k}\" AS VARCHAR) FROM raw.{dim} WHERE \"{k}\" IS NOT NULL)", why))
    elif low.startswith("required when status = done"):
        if "status" in actual:
            checks.append((f"\"status\" = 'Done' AND {q} IS NULL", f"{col}: required when status = Done"))
        if "started_date" in actual:
            checks.append((f"{dat(col)} < {dat('started_date')}", f"{col}: must be >= started_date"))
    elif low == "blank only when to do":
        if "status" in actual:
            checks.append((f"{q} IS NULL AND COALESCE(\"status\", '') <> 'To Do'", why))
    elif r == ">= 0":
        checks.append((f"{num(col)} < 0", why))
    elif low.startswith("0 to 1"):
        checks.append((f"{num(col)} < 0 OR {num(col)} > 1", why))
    elif re.fullmatch(r"(<=|>=)\s*[a-z_]+", low):
        op, other = re.fullmatch(r"(<=|>=)\s*([a-z_]+)", low).groups()
        if other in actual:
            f = dat if other.endswith("_date") else num
            bad = ">" if op == "<=" else "<"
            checks.append((f"{f(col)} {bad} {f(other)}", why))
        else:
            NOT_ENFORCED.append(f"{table}.{col}: {r}")
    elif low == "first day of month":
        checks.append((f"{dat(col)} IS NOT NULL AND {dat(col)} <> CAST(date_trunc('month', {dat(col)}) AS DATE)", why))
    elif low == "yyyy-mm":
        checks.append((f"{q} IS NOT NULL AND NOT regexp_matches(CAST({q} AS VARCHAR), '^\\d{{4}}-(0[1-9]|1[0-2])$')", why))
    elif low.startswith("exists in dim_"):
        dim = re.search(r"(dim_\w+)", low).group(1)
        if dim in all_tables:
            k = dim_key(con, dim, col)
            checks.append((exists_check(q, k, dim), why))
            if "active" in low:
                NOT_ENFORCED.append(f"{table}.{col}: 'active' part of '{r}'")
        else:
            NOT_ENFORCED.append(f"{table}.{col}: {r}")
    elif low.startswith("unique"):
        checks.append((f"{q} IS NOT NULL AND {q} IN (SELECT {q} FROM t GROUP BY 1 HAVING COUNT(*) > 1)",
                       f"{col}: duplicate value"))
        m = re.search(r"([A-Z]+)-(n+)", r)
        if m:
            pat = "^" + m.group(1) + "-\\d{" + str(len(m.group(2))) + "}$"
            checks.append((f"{q} IS NOT NULL AND NOT regexp_matches(CAST({q} AS VARCHAR), '{pat}')",
                           f"{col}: wrong format ({m.group(1)}-{m.group(2)})"))
    else:
        allowed = None
        m = re.fullmatch(r"P(\d)\.\.P(\d)", r)
        if m:
            allowed = [f"P{i}" for i in range(int(m.group(1)), int(m.group(2)) + 1)]
        elif "|" in r:
            allowed = [x.strip() for x in r.split("|")]
        elif re.fullmatch(r"[\w]+( or [\w]+)+", r):
            allowed = [x.strip() for x in r.split(" or ")]
        elif re.fullmatch(r"\d+(,\s*\d+)+", r):
            allowed = [x.strip() for x in r.split(",")]
        if allowed:
            vals = ",".join(f"'{sq(v)}'" for v in allowed)
            checks.append((f"{q} IS NOT NULL AND CAST({q} AS VARCHAR) NOT IN ({vals})", why))
        else:
            NOT_ENFORCED.append(f"{table}.{col}: {r}")
    return checks

def main():
    con = duckdb.connect(DB)
    con.execute("CREATE SCHEMA IF NOT EXISTS clean")
    # Re-run safe: rebuild all outputs from scratch every run
    con.execute("DROP TABLE IF EXISTS quarantine")
    con.execute("CREATE TABLE quarantine (table_name VARCHAR, reason VARCHAR, row_data VARCHAR)")
    con.execute("DROP TABLE IF EXISTS etl_summary")
    con.execute("""CREATE TABLE etl_summary (table_name VARCHAR, rows_in BIGINT,
                   rows_passed BIGINT, rows_quarantined BIGINT, status VARCHAR)""")

    all_tables = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='raw'").fetchall()]
    fact_tables = sorted(t for t in all_tables if t.startswith(("fact_", "dim_")))

    by_table = {}
    for feed, c, d, n, rule in con.execute(
            "SELECT feed, column_name, data_type, nullable, rule_or_allowed_values "
            "FROM raw.data_contracts").fetchall():
        m = re.search(r"\((\w+)\)\s*$", feed or "")
        if m:
            by_table.setdefault(m.group(1), []).append((c, d, n, rule))

    for table in fact_tables:
        rows_in = con.execute(f"SELECT COUNT(*) FROM raw.{table}").fetchone()[0]

        if table not in by_table:
            con.execute(f"CREATE OR REPLACE TABLE clean.{table} AS SELECT * FROM raw.{table}")
            con.execute(f"INSERT INTO etl_summary VALUES ('{table}', {rows_in}, {rows_in}, 0, "
                        f"'NO CONTRACT - not validated')")
            continue

        actual = [r[0] for r in con.execute(f"DESCRIBE raw.{table}").fetchall()]
        contract_cols = [c for c, *_ in by_table[table]]
        extra = set(actual) - set(contract_cols)
        missing = set(contract_cols) - set(actual)
        if extra:   print(f"WARNING {table}: unexpected new columns {sorted(extra)} (kept, not validated)")
        if missing: print(f"WARNING {table}: contract columns missing from data {sorted(missing)}")

        con.execute(f"CREATE OR REPLACE TEMP TABLE t AS "
                    f"SELECT row_number() OVER () AS _rn, * FROM raw.{table}")

        cases = []
        for col, dtype, nullable, rule in by_table[table]:
            if col not in actual:
                continue
            for cond, reason in build_checks(con, table, col, dtype, nullable, rule, actual, all_tables):
                cases.append(f"WHEN {cond} THEN '{sq(reason)}'")

        con.execute(f"CREATE OR REPLACE TEMP TABLE flagged AS "
                    f"SELECT _rn, CASE {' '.join(cases)} ELSE NULL END AS reason FROM t")
        con.execute(f"""INSERT INTO quarantine
                        SELECT '{table}', f.reason, CAST(t AS VARCHAR)
                        FROM flagged f JOIN t USING (_rn) WHERE f.reason IS NOT NULL""")
        con.execute(f"""CREATE OR REPLACE TABLE clean.{table} AS
                        SELECT * EXCLUDE (_rn) FROM t
                        WHERE _rn NOT IN (SELECT _rn FROM flagged WHERE reason IS NOT NULL)""")

        passed = con.execute(f"SELECT COUNT(*) FROM clean.{table}").fetchone()[0]
        bad = con.execute("SELECT COUNT(*) FROM quarantine WHERE table_name = ?", [table]).fetchone()[0]
        assert rows_in == passed + bad, f"{table}: rows_in {rows_in} != {passed} + {bad}"
        con.execute(f"INSERT INTO etl_summary VALUES ('{table}', {rows_in}, {passed}, {bad}, 'validated')")

    print("\n=== ETL SUMMARY ===")
    print(con.execute("SELECT * FROM etl_summary ORDER BY 1").df().to_string(index=False))

    print("\n=== QUARANTINE REASONS ===")
    print(con.execute("""SELECT table_name, reason, COUNT(*) AS n FROM quarantine
                         GROUP BY 1, 2 ORDER BY 1, 3 DESC""").df().to_string(index=False))

    if NOT_ENFORCED:
        print("\n=== RULES NOT ENFORCED (free text, cannot be checked automatically) ===")
        for x in sorted(set(NOT_ENFORCED)):
            print(" -", x)

if __name__ == "__main__":
    main()