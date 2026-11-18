# PulseIQ Analytics & Privacy-Preserving KPI Explorer

A production-grade, multi-page Streamlit analytics application featuring role-based access control (RBAC), hierarchical drill-downs, and automated privacy safeguards ($k$-anonymity and complementary suppression).

---

## 🚀 Dashboard Pages

1. **Receivables & Cash (`8_Receivables_and_Cash.py`)**: Tracks open invoices, ageing buckets, and accounts receivable against reconciliation keys.
2. **Cross-Department Impact (`9_Cross_department.py`)**: Analyzes headcount, attendance, and payroll metrics with data validation.
3. **AI Signals & Anomalies (`10_AI_signals.py`)**: Highlights payroll and attendance anomalies with risk rankings and predictive forecasting.
4. **Company Health Scorecard (`11_Health_scorecard.py`)**: Executive overview tracking key operational and financial metrics.
5. **Self-Service KPI Explorer (`13_Self_Service_KPI_Explorer.py`)**: Safe self-service analytics allowing users to drill down from Company → Department → Team while protecting sensitive data.

---

## 🔒 Privacy & Security Framework (Task 18)

* **$k$-Anonymity ($\ge 5$ employees):** Automatically suppresses groups or teams with fewer than 5 individuals to prevent individual identification.
* **Complementary Suppression:** Prevents subtraction attacks by hiding the next smallest group when one group is suppressed.
* **Role-Based Access Control (RBAC):** Restricts access to sensitive financial metrics (like payroll/salaries) based on user roles (**ADMIN**, **HR**, **EXECUTIVE**, **MANAGER**).

---

## Running the App Locally

1.Install dependencies:
pip install -r requirements.txt

2.Run the Streamlit application:
streamlit run phase-4/task18/app.py

### Phone test (live dashboard)

![Live dashboard on phone](docs/screenshots/phone-live-dashboard.jpeg)