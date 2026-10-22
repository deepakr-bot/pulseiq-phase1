import duckdb, glob, os, time, sys, csv
con = duckdb.connect("pulseiq.duckdb")
sev = {r["check_id"]: r["severity"] for r in csv.DictReader(open("dq/dq_checks_catalog.csv"))}
con.sql("""CREATE OR REPLACE TABLE dq_results(
  check_id VARCHAR, check_name VARCHAR, bad_rows INT,
  status VARCHAR, severity VARCHAR, run_time DOUBLE, run_at TIMESTAMP)""")
crit_fail = 0
for f in sorted(glob.glob("dq/checks/*.sql")):
    cid = os.path.basename(f)[:-4].upper().replace("_", "-")
    t = time.time()
    try:
        n = len(con.sql(open(f).read()).df())
        status = "PASS" if n == 0 else "FAIL"
    except Exception as e:
        n, status = -1, "ERROR"
        print(cid, e)
    s = sev.get(cid, "Warning")
    if status != "PASS" and s == "Critical":
        crit_fail += 1
    con.execute("INSERT INTO dq_results VALUES (?,?,?,?,?,?,now())",
                [cid, os.path.basename(f), n, status, s, round(time.time() - t, 3)])
print(con.sql("SELECT check_id, severity, bad_rows, status FROM dq_results ORDER BY 1").df().to_string())
print("\nCritical failures:", crit_fail)
if crit_fail:
    print("LOAD STOPPED")
    sys.exit(1)
print("LOAD OK")