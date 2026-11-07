import glob
import os
import sys

import duckdb
import pandas as pd

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
TOL = 1.0   # rupees
os.makedirs("reports", exist_ok=True)
con = duckdb.connect("pulseiq.duckdb", read_only=True)


def totals(src):
    return con.sql(f"SELECT COUNT(*) AS n_rows, SUM(gross_pay) AS gross, SUM(net_pay) AS net, "
                   f"SUM(employer_cost) AS employer_cost FROM {src}").df().iloc[0]


def mine(src):
    return con.sql(f"""
        SELECT strftime(LAST_DAY(p.period_end_date), '%Y-%m') AS _month, p.department_id,
               COALESCE(d.department_name, p.department_id) AS department,
               SUM(p.gross_pay) AS gross, SUM(p.net_pay) AS net, SUM(p.employer_cost) AS employer_cost
        FROM {src} p LEFT JOIN dw.dim_department d ON p.department_id = d.department_id
        GROUP BY 1, 2, 3""").df()


# ---------- A) My totals, before and after excluding bad rows ----------
asis, good = totals("dw.fact_payroll"), totals("dw.v_payroll_good")
mv = {
    "gross": con.sql("SELECT SUM(gross_pay) FROM main.m07_gross_pay").fetchone()[0],
    "net": con.sql("SELECT SUM(net_pay) FROM main.m08_net_pay").fetchone()[0],
    "employer_cost": con.sql("SELECT SUM(payroll_cost) FROM main.m09_payroll_cost").fetchone()[0],
}
print("\nA) Company totals")
a = pd.DataFrame({
    "measure": ["rows", "gross", "net", "employer_cost"],
    "as-is (all rows)": [asis["n_rows"], asis["gross"], asis["net"], asis["employer_cost"]],
    "after exclusion": [good["n_rows"], good["gross"], good["net"], good["employer_cost"]],
    "Task 4 metric views": [None, mv["gross"], mv["net"], mv["employer_cost"]],
})
a["excluded rows effect"] = a["after exclusion"] - a["as-is (all rows)"]
print(a.round(2).to_string(index=False))

mine_asis, mine_good = mine("dw.fact_payroll"), mine("dw.v_payroll_good")


# ---------- B) Answer key ----------
def read_all(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return {"csv": pd.read_csv(path, header=None, dtype=object)}
    if ext in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(path, sheet_name=None, header=None)
    return {}


def tidy(raw):
    raw = raw.dropna(how="all").dropna(axis=1, how="all")
    for i in range(min(len(raw), 15)):
        row = raw.iloc[i]
        vals = row.dropna()
        if len(vals) >= 2 and all(isinstance(v, str) for v in vals):
            df = raw.iloc[i + 1:].copy()
            df.columns = [str(c).strip() if pd.notna(c) else f"col{j}" for j, c in enumerate(row.values)]
            return df.reset_index(drop=True)
    return raw


def find_col(cols, *needles):
    for n in needles:
        for c in cols:
            if n in str(c).lower():
                return c
    return None


def to_month(s):
    if pd.api.types.is_numeric_dtype(s):
        t = s.astype("Int64").astype(str)
        d = pd.to_datetime(t, format="%Y%m%d", errors="coerce").fillna(pd.to_datetime(t, format="%Y%m", errors="coerce"))
        return d.dt.strftime("%Y-%m")
    return pd.to_datetime(s, errors="coerce").dt.strftime("%Y-%m")


def compare(sheet, mine_df, label):
    cols = list(sheet.columns)
    m = find_col(cols, "month", "period")
    d = find_col(cols, "department", "dept")
    meas = {"gross": find_col(cols, "gross"), "net": find_col(cols, "net"),
            "employer_cost": find_col(cols, "employer", "ctc", "payroll_cost", "total cost", "cost")}
    meas = {k: v for k, v in meas.items() if v is not None and v != d and v != m}
    if not meas or (m is None and d is None):
        return None
    k = sheet.copy()
    keys = []
    mm = mine_df.copy()
    if m is not None:
        k["_month"] = to_month(k[m])
        k = k.dropna(subset=["_month"])
        keys.append("_month")
    if d is not None:
        k["_dept"] = k[d].astype(str).str.strip()
        use_id = len(set(k["_dept"]) & set(mm["department_id"])) > 0
        mm["_dept"] = mm["department_id"] if use_id else mm["department"]
        keys.append("_dept")
    for col in meas.values():
        k[col] = pd.to_numeric(k[col], errors="coerce")
    kk = k.groupby(keys, as_index=False)[list(meas.values())].sum(min_count=1)
    kk = kk.rename(columns={v: f"key_{n}" for n, v in meas.items()})
    gg = mm.groupby(keys, as_index=False)[["gross", "net", "employer_cost"]].sum()
    mrg = gg.merge(kk, on=keys, how="outer")
    print(f"\n   [{label}] matched on {keys}, measures {list(meas)}, rows compared: {len(mrg)}")
    res = {}
    for n in meas:
        mrg[f"diff_{n}"] = mrg[n].fillna(0) - mrg[f"key_{n}"].fillna(0)
        bad = mrg[mrg[f"diff_{n}"].abs() > TOL]
        print(f"   {n}: rows that differ = {len(bad)}, total difference (mine - key) = {mrg[f'diff_{n}'].sum():,.2f}")
        if len(bad):
            print(bad[keys + [f"diff_{n}"]].head(15).round(2).to_string(index=False))
        res[n] = (mrg[n].sum(), mrg[f"key_{n}"].sum())
    return res


path = sys.argv[1] if len(sys.argv) > 1 else None
if path is None:
    files = [f for f in glob.glob("reference/*") if os.path.isfile(f)]
    path = files[0] if files else None

res_asis = res_good = None
if path is None:
    print("\nB) No answer key found. Copy unlock_PQ-09 into the reference folder and run this again.")
else:
    print("\nB) Answer key:", path)
    sheets = {n: tidy(df) for n, df in read_all(path).items()}
    if not sheets:
        print("   Could not read this file type. Save the key totals as CSV or XLSX in reference/.")
    for name, sh in sheets.items():
        print(f"\n   Sheet '{name}': {sh.shape[0]} rows, columns: {list(sh.columns)}")
        print(sh.head(8).to_string(index=False))
        r1 = compare(sh, mine_asis, f"{name}: as-is")
        r2 = compare(sh, mine_good, f"{name}: after exclusion")
        if r1 and r2 and res_good is None:
            res_asis, res_good = r1, r2
    if res_good is None:
        print("\n   Could not match month or department columns automatically.")
        print("   Paste the column names and the first 3 rows of the key (totals only) and I will adapt this script.")

# ---------- C) Reconciliation table ----------
lines = ["| Measure | My total, all rows | Difference vs key | My total, bad rows excluded | Answer key | Difference vs key |",
         "|---|---|---|---|---|---|"]
for n, label in [("gross", "Gross pay"), ("net", "Net pay"), ("employer_cost", "Employer cost")]:
    if res_good and n in res_good:
        before, key = res_asis[n]
        after = res_good[n][0]
        lines.append(f"| {label} | {before:,.2f} | {before - key:,.2f} | {after:,.2f} | {key:,.2f} | {after - key:,.2f} |")
    else:
        lines.append(f"| {label} | {a.loc[a.measure == n, 'as-is (all rows)'].iloc[0]:,.2f} | see key | "
                     f"{a.loc[a.measure == n, 'after exclusion'].iloc[0]:,.2f} | see key | see key |")
with open("reports/reconciliation_table.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\nSaved reports/reconciliation_table.md")
con.close()