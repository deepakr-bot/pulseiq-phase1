# Task 11: Profit and Loss and Expense Analytics

Source: pulseiq.duckdb, with the four tables (fact_ledger, dim_account, fact_expense, dim_vendor) loaded from PulseIQ_Dataset.xlsx. Zenith Nova Technologies (fictional). Period April 2025 to September 2026. Amounts in INR.

## Headline figures

- Total revenue: 1,260,930,052
- Total expenses: 1,036,264,914
- Profit: 224,665,138
- Overall margin: 17.8%

## Findings

1. **Margin moves a lot from month to month.** Monthly margin ranges from 8.3% (July 2025) to 27.2% (August 2026). The lowest months are July 2025, April 2026 and July 2026, at 8.3%, 13.7% and 13.4%.

2. **Salaries & Wages is the main cost.** It is about 76% of total expenses (about 787M of 1,036M). Incentives & Bonus, Office Rent and Cloud Hosting follow far behind.

3. **One landlord is the largest vendor.** Skyline Realty Holdings (Office Rent) is the top vendor at 16.9M excluding GST, about 10% of all bill spend.

## Revenue grew, but did margin fall?

I tested this claim against the data and it does not hold for this period.

- Revenue from April to September 2026 was about 471M, against about 389M in April to September 2025. That is growth of about 21%.
- Expenses over the same months grew about 17%, from about 326M to about 381M.
- Average monthly margin rose from 16.3% (April to September 2025) to 18.9% (April to September 2026).

So the premise is wrong for this comparison: revenue grew faster than costs, and margin improved. What remains is volatility, with a few weak months:

1. **Revenue dip.** July 2025 revenue fell to 56.8M, while expenses stayed at 52.1M, giving the 8.3% margin. Proof: monthly revenue and expenses on the P&L page.
2. **Expense jump.** April 2026 expenses rose to 72.0M from 59.6M in March, while revenue was 83.4M. Proof: the monthly table, March against April 2026.
3. **Mix shift.** Test whether a lower-margin revenue line grew as a share of total. Proof: revenue by account (4001 to 4004) per month. The analysis has not been run yet, so treat it as untested.

## Tie-out

Revenue, expenses and profit tie to the reconciliation answer key. The ledger originally overstated June 2026 expenses by 18,450 (known issue DQ-04: salary expense posted 18,450 above the payroll run). The page applies this as a labelled adjustment, so the reported and adjusted figures are both visible. The ledger balances, and no group accounts carry postings.

## Note on data

The data is the course dataset PulseIQ_Dataset.xlsx, a fictional company. The tie-out confirms internal consistency. It does not confirm agreement with real company books.