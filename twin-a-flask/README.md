# Expense Ledger, Twin A: Python + Flask

Household expense tracker in Omani rial. Feature-matched twin of `../twin-b-express` (Node + Express): same screens, same workflows, byte-identical HTML, CSV and JSON.

## At a glance

| | |
|---|---|
| Needs | Python 3.10 or newer |
| Dependencies | Flask 3 (runtime), pytest (tests). See `requirements.txt` |
| Run | `python run.py` and open http://127.0.0.1:5001 |
| Test | `python -m pytest -v` (41 tests) |
| Data | `data/ledger.json`, created from `seed.json` on first start |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python run.py                      # http://127.0.0.1:5001
```

Optional environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `5001` | Port to listen on |
| `LEDGER_DATA` | `data/ledger.json` | Data file. Twin B can use the same file |
| `LEDGER_DATA_LABEL` | the path | Text the Data screen shows for the data file |
| `LEDGER_TODAY` | today's date | Pins "today" (e.g. `2026-11-25`); used by the tests and the parity check |

## Test

```bash
python -m pytest -v
```

- `tests/test_rules.py`: 21 unit tests, named `test_frNN_...` after the requirement they prove. Twin B has the same 21 tests under the same names.
- `tests/test_scenarios.py`: runs the 20 shared scenarios in `tests/scenarios.json` (88 requests with exact expected responses) through the Flask test client.

Each test gets its own temporary data file, so tests never touch `data/ledger.json`.

## Project layout

```
run.py                 starts the server (port 5001)
seed.json              the 36 sample expenses (copy of spec/seed.json)
requirements.txt       Flask, pytest
ledger/
  __init__.py          create_app(): settings, error pages, headers      FR-01, FR-18
  routes.py            every URL, one function each                      FR-01 ... FR-18
  views.py             view models: ready-to-print strings for templates
  queries.py           totals, filters, sorting, chart, report maths     FR-02 ... FR-08, FR-13
  validation.py        the add/edit form rules                           FR-10
  money.py             baisa integers, rounding, formatting              FR-10, FR-17
  dates.py             ISO dates, month arithmetic                       FR-17
  text.py              trimming, URL encoding, plurals
  exports.py           CSV and JSON writers                              FR-14, FR-15
  store.py             JSON file storage, atomic writes                  FR-16, FR-17
  config.py            categories, sort options, every message
templates/             Jinja2: _top, _bottom, overview, expenses, form, delete, report, data, error
static/                app.css, fonts, favicon (same files as Twin B)
tests/                 conftest.py, test_rules.py, test_scenarios.py, scenarios.json
```

Every module starts with "Mirrors twin-b-express/src/<name>.js". The two builds have the same structure, so a fix in one can be found in the other.

## Routes

| Method | Path | Screen or output |
|---|---|---|
| GET | `/` (`?month=YYYY-MM`) | Overview |
| GET | `/expenses` (`?month=&category=&q=&sort=`) | Expense list |
| GET, POST | `/expenses/new`, `/expenses` | Add expense |
| GET, POST | `/expenses/<id>/edit`, `/expenses/<id>` | Edit expense |
| GET, POST | `/expenses/<id>/delete` | Delete confirmation, delete |
| GET | `/reports` (`?month=`) | Monthly report |
| GET | `/export/expenses.csv`, `/export/report.csv` | CSV downloads |
| GET | `/api/expenses`, `/api/summary` | JSON |
| GET, POST | `/data`, `/data/reset`, `/data/clear` | Data tools |

Successful POSTs answer `303 See Other`. Invalid forms come back with `422` and the messages. Unknown pages get `404`, and wrong methods get `405`.
