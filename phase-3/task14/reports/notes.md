# Task 14: AI signals

AI-generated, for human review.

## Chart 1: Anomalies by type

Money at risk is available only for payroll anomalies (184 of 405, about 31.4M in total). Attendance anomalies are counted but have no money value. The largest type is STATISTICAL_OUTLIER, at about 19.4M.

## Chart 2: Largest payroll anomalies

The table ranks payroll anomalies by money at risk, largest first. Each row is a flagged employee-month, with the model's reason and score.

## Chart 3: Forecast with 80% range

The shaded band is the range the model expects the value to fall in 80% of the time. The forecast covers October 2026 to March 2027. These months have no actual values yet, so the band cannot yet be checked against what happened.

## Forecast error

Forecast error for past months cannot be calculated from this dataset. Every forecast row shows "awaiting actuals", so no average error is reported.

## Limits

The forecast is a trend-and-seasonality baseline, and the anomaly scores are model outputs. Treat both as signals for review, not as decisions.
