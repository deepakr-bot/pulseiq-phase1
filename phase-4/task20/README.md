# Task 20: Board Pack and Final Handover

Runs quality and reconciliation checks on the live warehouse, then builds a 9-slide board deck from the same data.

Status: checks run; two fail (freshness and headcount). Deck built from the current data.

## Files

- `quality_checks.py`: runs seven checks and writes `reports/quality_report.md`. Exits with code 1 if any check fails.
- `build_board_deck.py`: builds `reports/board_deck.pptx` from the warehouse. Reads the quality report for slide 9.
- `check_headcount.py`: diagnostic. Lists where `m01_headcount` and `fact_headcount_monthly` live, and the latest-month sum in each schema.

Outputs are written to `reports/` at the repo root.

## Board deck

| Slide | Content |
|---|---|
| 1 | Cover, with data refresh date |
| 2 | Five findings |
| 3 to 7 | One finding per slide: headcount, attrition, payroll cost, days sales outstanding, on-time delivery. Each has a chart, evidence and a recommendation. |
| 8 | What we are not recommending yet, and why |
| 9 | Data quality and reconciliation results |

The recommendations were written by the script and are drafts. Check each one against its chart before presenting.

## Quality checks

| Check | Last result |
|---|---|
| ETL freshness: last run within 7 days | FAIL (27 days old) |
| ETL row balance: in = passed + quarantined | PASS |
| Reconcile headcount: metric view = fact table | FAIL (440 vs 441) |
| Reconcile payroll: cost view = fact table | PASS |
| Range: attrition between 0 and 100 | PASS |
| Logic: on-time tasks never exceed tasks with due dates | PASS |
| Info: quarantined rows listed for review | PASS (20 rows in `fact_task`) |

## Requirements

From the repo root:

```bash
pip install -r requirements.txt
```

## How to run

Run the checks first, because the deck reads the quality report.

```bash
cd phase-4\task20
python quality_checks.py
python build_board_deck.py
```

The first command prints PASS or FAIL for each check. The second prints the path to the saved deck.

To check which schema holds the headcount table:

```bash
python check_headcount.py
```

## Known limits

- The data was last refreshed 2026-10-21, about four weeks before this release.
- The headcount gap (440 vs 441) is disclosed and not yet investigated.
- Lineage and recommendations are hand-written and need review before they are presented as fact.
- Quarantined rows (20 in `fact_task`) are listed but not yet investigated.

See `RELEASE_NOTES.md` at the repo root for the full list of changes and limits.