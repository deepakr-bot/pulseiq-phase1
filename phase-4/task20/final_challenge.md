# Final Challenge: k-Anonymity Compliance and Audit Endpoint

## 1. What I built

I built a read-only REST API endpoint that reports departmental k-anonymity compliance (k = 5) for payroll data. It reads department headcounts from the PulseIQ DuckDB warehouse, excludes any department with an average headcount below 5, and returns the results with structured metadata for audit review.

* **Branch and commit:** `feature/audit-compliance-endpoint` (`[7a30534]`)
* **Route:** `GET /audit/compliance-report`
* **File and function:** `phase-4/task19/main.py`, `get_compliance_report()`
* **What it returns:** `status`, `k_anonymity_threshold` (5), `shown_departments_count`, `hidden_departments_count`, `freshness_statement`, `last_refresh`, and a `departments` list. Each department entry includes its ID, name, average headcount and minimum headcount.

## 2. Why I chose it

* **Why this and not the other options:** Freshness checks and the headcount gap are useful, but the project overview requires that small groups be hidden. Payroll totals for very small teams can identify individuals, so I chose the endpoint that enforces that rule in the API rather than only in the dashboard.
* **Requirement addressed:** The overview states that salary-level data must be protected and small groups must be hidden.

## 3. How I tested it

* **Test 1 (normal run):** I sent `GET http://127.0.0.1:8000/audit/compliance-report` to the running Uvicorn server. It returned HTTP 200 with this response:

```json
{"status":"success","k_anonymity_threshold":5,"shown_departments_count":10,"hidden_departments_count":1,"freshness_statement":"Data refreshed at 2026-10-21 13:40:18 UTC.","last_refresh":"2026-10-21 13:40:18 UTC","departments":[{"department_id":"D01","department":"Engineering","avg_employees":153.5,"min_employees":143},{"department_id":"D02","department":"Product & Design","avg_employees":25.38888888888889,"min_employees":23},{"department_id":"D03","department":"Data & AI","avg_employees":50.611111111111114,"min_employees":47},{"department_id":"D04","department":"Sales","avg_employees":42.77777777777778,"min_employees":39},{"department_id":"D05","department":"Marketing","avg_employees":12.444444444444445,"min_employees":10},{"department_id":"D06","department":"Customer Support","avg_employees":51.666666666666664,"min_employees":46},{"department_id":"D07","department":"Human Resources","avg_employees":16.555555555555557,"min_employees":14},{"department_id":"D08","department":"Finance & Accounts","avg_employees":16.5,"min_employees":15},{"department_id":"D09","department":"Operations & IT","avg_employees":27.88888888888889,"min_employees":24},{"department_id":"D10","department":"Legal & Compliance","avg_employees":9.444444444444445,"min_employees":8}]}
```

* **Test 2 (threshold check):** I queried `dw.v_payroll_dept_size` directly. It returns 11 departments. Exactly one has an average below 5: a single-person department with an average of 1.0. The endpoint hid it and reported `hidden_departments_count: 1`, which matches the response above.
* **Code review:** I read the function to confirm that it opens the database read-only, closes the connection in a `finally` block, and converts `duckdb.Error` into an HTTP 500 response. I did not force a database error to test that path.
* **Route registration:** I confirmed the route exists with `Select-String`, and that Uvicorn starts cleanly from `phase-4\task19` with `uvicorn main:app --reload`.
* **Freshness helpers:** I ran `freshness_statement()` and `get_last_refresh()` directly. Both returned 2026-10-21 13:40:18 UTC, the same values the endpoint returns.

## 4. What the output shows

* **Which departments appear, and why:** Ten departments appear because each has an average headcount of at least 5. One department with an average below 5 is excluded and counted in `hidden_departments_count`. I have not named it here, since naming a one-person group in a governance document is the kind of disclosure the endpoint is meant to prevent.
* **What `status` means:** `"success"` means the read-only query ran without error and the rule was applied to its results. It is not a formal proof of compliance.
* **What the freshness fields mean:** `freshness_statement` and `last_refresh` are read from the ETL log by the helper functions `freshness_statement()` and `get_last_refresh()`. Both show 2026-10-21 13:40:18 UTC, which is when the warehouse ETL last finished. They are not the time the report was generated.

## 5. Limits

* **Scope of the rule:** The endpoint checks department-level group sizes from `dw.v_payroll_dept_size`. It does not apply the dashboard's small-department-month rule to individual months, and it does not protect multi-dimensional drill-downs where several filters combined could isolate fewer than 5 people.
* **Measure used:** It uses average headcount (`avg_employees >= 5`), the measure defined in the warehouse view. It does not use minimum headcount. A department could fall below 5 in some months even with an average of 5 or more, so this rule is weaker than a minimum-based one.
* **Not a certification:** This is an internal engineering control. It is not a legal, SOC 2 or GDPR certification from an external auditor.
* **Data age:** The data was last refreshed on 2026-10-21, 27 full days before I ran these checks on 18 November 2026. It is a historical snapshot, not a live feed.
* **Disclosure:** The `hidden_departments_count` field and the ten visible names together let a reader infer that exactly one more department exists. That is a differencing risk in a public build.

## 6. What I would build next

* **Improvement:** Add automated pytest tests that check the rule rather than fixed numbers. Each shown department should have `avg_employees >= 5`, and `hidden_departments_count` should equal the number of rows in `dw.v_payroll_dept_size` below 5.
* **What I would verify first:** Whether exposing `hidden_departments_count` publicly creates a differencing risk, and whether it should be removed or aggregated in public builds.