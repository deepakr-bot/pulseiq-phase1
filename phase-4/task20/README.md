# Task 20: Board Pack and Final Handover

Runs quality and reconciliation checks on the live warehouse, builds a 9-slide board deck from the same data, and records the release.

**Release tag:** https://github.com/deepakr-bot/pulseiq-phase1/releases/tag/v1.0.0 (commit `dfad8a8`)

**Final challenge write-up:** `phase-4/task20/final_challenge.md`

## Files

- `quality_checks.py`: runs seven checks on the warehouse and writes `reports/quality_report.md`. Exits with code 1 if any check fails.
- `build_board_deck.py`: builds `reports/board_deck.pptx`. Reads the quality report for slide 9.
- `check_headcount.py`: diagnostic. Shows where `m01_headcount` and `fact_headcount_monthly` live, and the latest-month sum in each schema.
- `final_challenge.md`: write-up for the compliance endpoint.

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

Last run: 18 November 2026.

| Check | Result |
|---|---|
| ETL freshness: last run within 7 days | FAIL (27 days old) |
| ETL row balance: in = passed + quarantined | PASS |
| Reconcile headcount: metric view = fact table | FAIL (440 vs 441) |
| Reconcile payroll: cost view = fact table | PASS |
| Range: attrition between 0 and 100 | PASS |
| Logic: on-time tasks never exceed tasks with due dates | PASS |
| Info: quarantined rows listed for review | PASS (20 rows in `fact_task`) |

## Run

From the repo root, with the virtual environment active:

```bash
pip install -r requirements.txt
cd phase-4\task20
python quality_checks.py
python build_board_deck.py
```

The first command prints PASS or FAIL for each check. The second prints the path to the saved deck.

## Known limits

- The data was last refreshed 21 October 2026, about four weeks before this release.
- The headcount gap (440 vs 441) is disclosed and not yet investigated.
- Lineage and deck recommendations are written by hand and need review before they are presented as fact.
- Quarantined rows (20 in `fact_task`) are listed but not yet investigated.
- Scheduled refresh is not running.

See `RELEASE_NOTES.md` at the repo root for the full list of changes and limits.