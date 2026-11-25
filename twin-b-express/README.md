# Expense Ledger, Twin B: Node.js + Express

Household expense tracker in Omani rial. Feature-matched twin of `../twin-a-flask` (Python + Flask): same screens, same workflows, byte-identical HTML, CSV and JSON.

## At a glance

| | |
|---|---|
| Needs | Node.js 18.17 or newer (npm comes with it) |
| Dependencies | Express 5 and EJS (runtime). Tests use only Node's built-in `node:test` and `fetch` |
| Run | `npm start` and open http://127.0.0.1:5002 |
| Test | `npm test` (41 tests) |
| Data | `data/ledger.json`, created from `seed.json` on first start |

## Setup

```bash
npm install
```

## Run

```bash
npm start                          # http://127.0.0.1:5002   (same as: node server.js)
```

Optional environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `5002` | Port to listen on |
| `LEDGER_DATA` | `data/ledger.json` | Data file. Twin A can use the same file |
| `LEDGER_DATA_LABEL` | the path | Text the Data screen shows for the data file |
| `LEDGER_TODAY` | today's date | Pins "today" (e.g. `2026-11-25`); used by the tests and the parity check |

## Test

```bash
npm test
```

- `test/rules.test.js`: 21 unit tests, named `FR-NN ...` after the requirement they prove. Twin A has the same 21 tests under the same names.
- `test/scenarios.test.js`: runs the 20 shared scenarios in `test/scenarios.json` (88 requests with exact expected responses) against a real server on a free port, using the built-in `fetch`.

Each test gets its own temporary data file, so tests never touch `data/ledger.json`.

## Project layout

```
server.js              starts the server (port 5002)
seed.json              the 36 sample expenses (copy of spec/seed.json)
package.json           express, ejs; scripts: start, test
src/
  app.js               createApp(): settings, error pages, headers       FR-01, FR-18
  routes.js            every URL, one handler each, plus 405 handlers    FR-01 ... FR-18
  views.js             view models: ready-to-print strings for templates
  queries.js           totals, filters, sorting, chart, report maths     FR-02 ... FR-08, FR-13
  validation.js        the add/edit form rules                           FR-10
  money.js             baisa integers, BigInt rounding, formatting       FR-10, FR-17
  dates.js             ISO dates, month arithmetic                       FR-17
  text.js              trimming, URL encoding, plurals
  exports.js           CSV and JSON writers                              FR-14, FR-15
  store.js             JSON file storage, atomic writes                  FR-16, FR-17
  config.js            categories, sort options, every message
views/                 EJS: _top, _bottom, overview, expenses, form, delete, report, data, error
public/                app.css, fonts, favicon (same files as Twin A)
test/                  helpers.js, rules.test.js, scenarios.test.js, scenarios.json
```

Every module starts with "Mirrors twin-a-flask/ledger/<name>.py". The two builds have the same structure, so a fix in one can be found in the other.

## Matching Flask, point by point

Express and Flask differ in a few defaults. Twin B sets these explicitly so the two builds answer every request the same way:

- strict, case-sensitive routing (`/expenses/` and `/Expenses` are 404, as in Flask)
- `405 Method Not Allowed` pages via `.all()` handlers (Flask does this on its own)
- no `X-Powered-By` header, no ETags on pages, and the first value wins when a form field repeats
- `[...text].length` counts characters the way Python's `len()` does, so an emoji counts as 1, not 2
- rounding uses `BigInt`, so totals never touch floating point

## Routes

| Method | Path | Screen or output |
|---|---|---|
| GET | `/` (`?month=YYYY-MM`) | Overview |
| GET | `/expenses` (`?month=&category=&q=&sort=`) | Expense list |
| GET, POST | `/expenses/new`, `/expenses` | Add expense |
| GET, POST | `/expenses/:id/edit`, `/expenses/:id` | Edit expense |
| GET, POST | `/expenses/:id/delete` | Delete confirmation, delete |
| GET | `/reports` (`?month=`) | Monthly report |
| GET | `/export/expenses.csv`, `/export/report.csv` | CSV downloads |
| GET | `/api/expenses`, `/api/summary` | JSON |
| GET, POST | `/data`, `/data/reset`, `/data/clear` | Data tools |
