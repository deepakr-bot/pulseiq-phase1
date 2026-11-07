import duckdb
con = duckdb.connect("pulseiq.duckdb")

def test(check, tables, bad_sql, mode="count"):
    try:
        sql = open(f"dq/checks/{check}.sql").read()
        for full in tables:
            t = full.split(".")[1]
            con.sql(f"CREATE OR REPLACE TEMP TABLE t_{t} AS SELECT * FROM {full}")
            sql = sql.replace(full, f"t_{t}")
        before = con.sql(sql).df()
        con.sql(bad_sql)
        after = con.sql(sql).df()
        if mode == "count":
            ok = len(after) > len(before)
        else:
            ok = set(map(tuple, after.values.tolist())) != set(map(tuple, before.values.tolist()))
        print(check.upper(), "CAUGHT" if ok else "NOT CAUGHT", f"({len(before)} -> {len(after)} bad rows)")
    except Exception as e:
        print(check.upper(), "TEST ERROR:", e)

test("dq_c01", ["dw.fact_payroll", "dw.fact_ledger"],
     "UPDATE t_fact_payroll SET employer_cost = employer_cost + 100000 WHERE payroll_item_id = (SELECT MIN(payroll_item_id) FROM t_fact_payroll)", "content")

test("dq_c02", ["dw.fact_ledger"],
     "UPDATE t_fact_ledger SET debit = debit + 500 WHERE line_id = (SELECT MIN(line_id) FROM t_fact_ledger)")

test("dq_c03", ["dw.fact_payroll"],
     """INSERT INTO t_fact_payroll SELECT * FROM t_fact_payroll WHERE (employee_id, run_id) IN
        (SELECT employee_id, run_id FROM t_fact_payroll GROUP BY 1,2 HAVING COUNT(*) = 1) LIMIT 1""")

test("dq_c04", ["dw.fact_payroll", "dw.dim_employee"],
     "DELETE FROM t_dim_employee WHERE employee_id = (SELECT f.employee_id FROM t_fact_payroll f JOIN t_dim_employee d ON f.employee_id = d.employee_id LIMIT 1)")

test("dq_c05", ["dw.fact_attendance_monthly", "dw.dim_employee"],
     """UPDATE t_fact_attendance_monthly SET period_end_date = DATE '2099-12-31' WHERE attendance_fact_id =
        (SELECT a.attendance_fact_id FROM t_fact_attendance_monthly a JOIN t_dim_employee d ON a.employee_id = d.employee_id
         AND CAST(d.is_current AS VARCHAR) IN ('Y','true','True','1')
         WHERE d.exit_date IS NOT NULL AND CAST(a.period_end_date AS DATE) <= LAST_DAY(CAST(d.exit_date AS DATE)) LIMIT 1)""")

test("dq_c06", ["dw.fact_attendance_monthly", "dw.fact_payroll"],
     """UPDATE t_fact_attendance_monthly SET unpaid_absence_days = unpaid_absence_days + 10 WHERE attendance_fact_id =
        (SELECT a.attendance_fact_id FROM t_fact_attendance_monthly a JOIN t_fact_payroll p
         ON a.employee_id = p.employee_id AND a.period_end_date = p.period_end_date
         WHERE ABS(a.unpaid_absence_days - p.lop_days) <= 0.5 LIMIT 1)""")

test("dq_c07", ["dw.fact_invoice"],
     """UPDATE t_fact_invoice SET amount_paid = total_amount + 1000 WHERE invoice_id =
        (SELECT invoice_id FROM t_fact_invoice WHERE amount_paid <= total_amount AND balance_due >= 0 LIMIT 1)""")

test("dq_c08", ["dw.fact_expense"],
     """UPDATE t_fact_expense SET gst_amount = gst_amount + 500 WHERE expense_id =
        (SELECT expense_id FROM t_fact_expense WHERE ABS(total_amount - (amount_excl_gst + gst_amount)) <= 0.01 LIMIT 1)""")

test("dq_c09", ["dw.fact_task"],
     "UPDATE t_fact_task SET status = 'Done', completed_date = NULL WHERE task_id = (SELECT MIN(task_id) FROM t_fact_task)")

test("dq_c10", ["dw.fact_leave"],
     """UPDATE t_fact_leave SET end_date = start_date, start_date = end_date WHERE leave_request_id =
        (SELECT leave_request_id FROM t_fact_leave WHERE end_date > start_date LIMIT 1)""")

test("dq_c11", ["dw.fact_attrition_risk"],
     """UPDATE t_fact_attrition_risk SET as_of_date = as_of_date - INTERVAL 30 DAY WHERE prediction_id =
        (SELECT prediction_id FROM t_fact_attrition_risk
         WHERE as_of_date >= (SELECT MAX(as_of_date) FROM t_fact_attrition_risk) - 7 LIMIT 1)""")

test("dq_c12", ["dw.dim_employee"],
     """INSERT INTO t_dim_employee SELECT * REPLACE (employee_key + 100000 AS employee_key)
        FROM t_dim_employee WHERE valid_to IS NOT NULL LIMIT 1""")

test("dq_c13", ["main.etl_run_log"],
     "UPDATE t_etl_run_log SET finished_at = finished_at - INTERVAL 3 DAY")

test("dq_c14", ["dw.dim_employee"],
     """DELETE FROM t_dim_employee WHERE employee_key IN (
        SELECT employee_key FROM (SELECT employee_key, ROW_NUMBER() OVER
        (PARTITION BY department_id ORDER BY employee_key) rn FROM t_dim_employee) WHERE rn > 2)""")