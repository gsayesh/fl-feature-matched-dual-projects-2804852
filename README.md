# Expense Ledger: twin builds

Two separate, runnable projects with the same screens, workflows and outputs. Switch between them and you will not notice a difference: every page, CSV file and JSON response is byte-for-byte identical.

| | Twin A | Twin B |
|---|---|---|
| Stack | Python 3.10+ · Flask 3 · Jinja2 | Node.js 18.17+ · Express 5 · EJS |
| Folder | [`twin-a-flask/`](twin-a-flask/README.md) | [`twin-b-express/`](twin-b-express/README.md) |
| Opens at | http://127.0.0.1:5001 | http://127.0.0.1:5002 |
| Tests | pytest, 41 tests | node:test, 41 tests |

**Start here:** [`docs/expense-ledger-twins.pdf`](docs/expense-ledger-twins.pdf) (15 pages: requirements, traceability, both builds side by side, evidence, setup) or the [interactive preview](index.html).

The app is a small household expense tracker in Omani rial (OMR): an overview with a chart, an expense list with filters, search and sort, add / edit / delete with server-side validation, a monthly report, CSV and JSON exports, and data tools. The requirements are in **[docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)** (18 requirements, every message, and a traceability matrix).

## Run both (about 2 minutes)

**Twin A** needs Python 3.10 or newer.

```bash
cd twin-a-flask
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                      # http://127.0.0.1:5001
python -m pytest -v                # 41 passed
```

**Twin B** needs Node.js 18.17 or newer.

```bash
cd twin-b-express
npm install
npm start                          # http://127.0.0.1:5002
npm test                           # 41 passed
```

Each build creates `data/ledger.json` from the sample data on first start. To start a walkthrough from scratch, use **Data → Restore sample data** or delete that file.

## Prove they are identical

```bash
python3 tools/parity_check.py --python twin-a-flask/.venv/bin/python
```

Starts both builds, follows every link from the overview, replays all 20 shared scenarios (including adds, edits, deletes and validation errors) and compares status, headers and body byte for byte. Last run: **218 of 218 responses identical**, and the two data files were byte-identical afterwards (`docs/parity-report.txt`).

`tools/screenshots.py` drives both builds through the same clicks in Chrome. **15 of 15 screens were pixel-identical** (`docs/screens/`).

## Walkthrough checklist

Open both builds in two browser tabs and do each step in both:

1. **Overview**: November 2026, OMR 496.850 spent, down 6.5 % on October. Use the arrows to move between months; August is empty.
2. **Expenses**: filter November + Utilities (3 expenses, OMR 45.450), search `grocer`, sort by amount.
3. **Add expense**: submit an empty form to see the four messages, then add a valid one. The list shows "Expense added."
4. **Edit**: open any row, change the amount, save. The list shows "Expense updated."
5. **Delete**: the confirmation page, then "Expense deleted." The deleted number is never reused.
6. **Reports**: every category against the previous month. Export the CSV.
7. **Data**: try "Delete all expenses" without the tick, then restore the sample data.

## What is where

```
README.md                  this page
docs/
  expense-ledger-twins.pdf the illustrated 15-page document (both project ZIPs attached)
  REQUIREMENTS.md          requirements write-up + traceability matrix (generated)
  parity-report.txt        last parity check, request by request
  test-output-twin-a.txt   last pytest run
  test-output-twin-b.txt   last node:test run
  screens/                 the same 15 screens captured from both builds
spec/                      framework-neutral source of truth
  requirements.json        FR-01 ... FR-18, every message, categories
  scenarios.json           20 scenarios / 88 steps both test suites run
  seed.json                the 36 sample expenses
  assets/                  the one stylesheet, fonts and icon both builds serve
twin-a-flask/              Twin A, self-contained (see its README)
twin-b-express/            Twin B, self-contained (see its README)
tools/
  sync_shared.py           copies spec/ files into both twins (--check to verify)
  parity_check.py          runs both builds and compares every response
  screenshots.py           captures and pixel-compares both builds (needs Playwright)
  trace.py                 rebuilds docs/REQUIREMENTS.md and reruns both suites
  build_docs.py            rebuilds the PDF document, the preview page and the ZIPs
dist/                      twin-a-flask.zip, twin-b-express.zip (clean copies for hand-over)
index.html, demo/          interactive preview of the captured screens (GitHub Pages)
```

## How the two builds stay identical

- **One spec, two codebases.** Each build has its own code, written for its framework: Flask blueprint and Jinja2 templates in Twin A, Express router and EJS templates in Twin B. Module for module, they mirror each other (`ledger/money.py` ↔ `src/money.js`, and so on), and every requirement is tagged `FR-xx` in the comments of both.
- **Rules the runtimes disagree on are written out by hand.** Money is whole baisa (integers, never floats) with half-away-from-zero rounding, text length counts Unicode characters, trimming uses ASCII whitespace only, and URL encoding and CSV quoting are spelled out. Python and JavaScript have different defaults for all of these.
- **Shared tests.** `spec/scenarios.json` holds the requests and the exact expected responses. Both suites run it, and their 21 unit tests have the same names.
- **Only neutral files are shared,** as copies, so each folder runs on its own: the stylesheet, fonts, sample data and scenarios.
