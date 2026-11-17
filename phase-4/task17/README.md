# Task 17: Live dashboard

A public dashboard of PulseIQ company and department measures, published as aggregates only.

## Live link


[Open the live dashboard](https://pulseiq-phase1-ydkftnpf9rqccbct2ht8tc.streamlit.app/Live_dashboard)

Shown on a phone with mobile data:
- `reports/task17_phone_1.jpeg`
- `reports/task17_phone_2.jpeg`

## What it shows

- **Home:** the latest month's headcount, revenue and operating margin, with the data cut-off date.
- **Company:** revenue, net profit and operating margin by month, with a month selector.
- **Departments:** headcount, attendance, overtime and attrition by department for a chosen month.

## Data

The live app reads three small files in `data/`, made by `export_aggregates.py`:
- `company_monthly.csv`: company totals by month
- `department_monthly.csv`: department figures by month
- `meta.json`: the data cut-off and the minimum group size

The full warehouse (`pulseiq.duckdb`) is not published. Only these aggregates are.

## Privacy rule

Departments with fewer than 5 people in a month are not shown. Individual employees are never shown.

## How to run locally

```bash
pip install -r requirements.txt
python export_aggregates.py
streamlit run phase-4\task17\app.py

```

## Refresh

`.github/workflows/refresh-data.yml` re-exports the data every Monday at 05:00 UTC and commits any change. Streamlit Community Cloud redeploys the app from `main` after each commit.

## Hosting choice

Checked on 2026-11-17 against each provider's pricing or limits page. Copy each figure exactly as the page shows it, and write "not stated" where a figure is not on the page.

| Option | Free limits | Data size | Sleep behaviour | Price |
| --- | --- | --- | --- | --- |
| Streamlit Community Cloud | Public apps free; ~2.7 GB RAM | ~200 MB repo limit | Sleeps after 12 hours of inactivity; wakes automatically on user request | $0 (Free) |
| Metabase Cloud | 14-day free trial only | not stated | not stated | $100/mo ($90/mo billed yearly) |
| Apache Superset (self-hosted) | Free & open source | not stated | not stated | $0 (Free code; server cost not stated) |
| Preset Cloud (managed Superset) | Free Starter Plan (up to 5 users) | not stated | not stated | $20/user/mo (Preset Pro) |

GitHub's rule for repository files: a single file over 100 MB cannot be pushed. Source: [GitHub large file docs](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

I chose Streamlit Community Cloud because it integrates directly with GitHub for instant, serverless Python deployments at zero cost.

When the app went to sleep after 12 hours of inactivity, it displayed a prompt to wake up, booting within a few seconds upon clicking; we handle this by keeping our aggregated data files lightweight so startup remains fast.

## Limit decision (200 MB)

We published only pre-aggregated monthly summary files (`company_monthly.csv`, `department_monthly.csv`, and `meta.json`), while leaving out the full `pulseiq.duckdb` data warehouse because it holds sensitive employee-level records and individual logs. File size was never the limiting factor, as the aggregates total only a few kilobytes.

## Stranger test

A test user opened the link on mobile data on 2026-11-17 and took 6 seconds to find the latest headcount (388) right on the Home screen without any help. They did not get stuck anywhere, though they noted that the multi-select month filters on the Company tab take up vertical space on a narrow phone screen.
