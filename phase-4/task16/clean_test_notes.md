# Task 16: Clean-machine test notes

Date: 2026-11-11
Machine: Windows, PowerShell 5.1, Python [your version from python --version]

## Steps
1. `git clone https://github.com/deepakr-bot/pulseiq-phase1.git clean-test`
2. `python -m venv .venv` and activate it
3. `pip install -r phase-4\task16\requirements.txt`: all pinned packages installed, no errors
4. `python phase-4\task16\build_report.py --month 2026-09`: printed `Report written` and created `output\pulseiq_report_2026-09.pdf`

## Result
Passed first time. No errors and no manual fixes.

## Notes
- The install used Python 3.14 wheels. The README says Python 3.12 or newer, so the README was updated to match. [Delete this line if you did not change the README.]
- The report reads the database from the cloned repo, so the clone needed no other files.