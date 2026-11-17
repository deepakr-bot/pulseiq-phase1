### Task 18: Break-It Notes & Adversarial Testing Log

1. **Small Group Drill-Down Attack ($k$-Anonymity Check)**
   * **Test Action:** Logged in as HR and drilled down through the hierarchy (Company → Department → Team) to inspect tiny teams.
   * **Vulnerability Found:** Teams with 1 to 4 members exposed individual employee records and vulnerable metrics.
   * **Fix Implemented:** Enforced a strict minimum group size threshold ($k \ge 5$). Any group falling below 5 members is automatically caught and filtered out, replacing the chart and table with a security warning banner: *"Privacy Protection Active: X group(s) with fewer than 5 employees have been hidden."*

2. **Intersection Attack (Multi-Dimensional Slicing)**
   * **Test Action:** Selected a department-level view and applied a secondary breakdown across *Location* and *Grade* simultaneously to deliberately slice headcount down to 1–2 individuals per bucket.
   * **Vulnerability Found:** Fine-grained slicing bypassed single-dimension filters.
   * **Fix Implemented:** Configured $k$-anonymity evaluation to run *after* grouping across all selected dimensions (`group_cols`) simultaneously, ensuring tiny intersecting slices are successfully isolated and suppressed.

3. **Subtraction / Differencing Attack**
   * **Test Action:** Inspected a department of 15 people split into Team A (12 people) and Team B (3 people). Although Team B was hidden, a user could subtract Team A's visible total from the parent department total ($15 - 12 = 3$) to mathematically deduce Team B's headcount and metrics.
   * **Vulnerability Found:** Mathematical deduction leaks values of suppressed groups.
   * **Fix Implemented:** Implemented **complementary suppression** (`if suppressed_count == 1`). If exactly one group is suppressed, the system automatically suppresses the next smallest valid group so totals cannot be reverse-engineered via subtraction.

4. **Role Escalation Check**
   * **Test Action:** Switched user profile to a `MANAGER` role and attempted to access restricted financial metrics (e.g., *Avg Salary*, *Total Payroll Cost*) or view data outside their assigned department.
   * **Vulnerability Found:** Unauthorized data access across organizational boundaries.
   * **Fix Implemented:** Restricted the allowed metric dropdown based on the user's role profile and pre-filtered the underlying dataframe to the user's assigned `department_id` before rendering any UI elements.