'use strict';
/**
 * CSV and JSON outputs (FR-14, FR-15). Mirrors twin-a-flask/ledger/exports.py.
 *
 * The CSV writer is hand-rolled (no csv library) so its quoting rules match
 * Twin A exactly: RFC 4180, CRLF, UTF-8 with BOM, formula-injection guard.
 */

const dates = require('./dates');
const { CATEGORY_LABELS, CURRENCY } = require('./config');
const { fmtPlain, tenthsPlain } = require('./money');

const BOM = '\uFEFF'; // UTF-8 byte-order mark so Excel detects UTF-8 (Arabic text)
const FORMULA_START = ['=', '+', '-', '@', '\t', '\r'];

/** One CSV cell. Text cells starting with a formula character get a leading apostrophe. */
function cell(value, text = true) {
  let s = String(value);
  if (text && FORMULA_START.some((ch) => s.startsWith(ch))) s = "'" + s;
  if ([',', '"', '\r', '\n'].some((ch) => s.includes(ch))) s = '"' + s.split('"').join('""') + '"';
  return s;
}

/** rows: array of arrays of already-converted cells. */
function document(rows) {
  return BOM + rows.map((row) => row.join(',') + '\r\n').join('');
}

function expensesCsv(rows) {
  const out = [['ID', 'Date', 'Description', 'Category', 'Amount (OMR)', 'Notes']];
  for (const r of rows) {
    out.push([
      cell(r.id, false),
      cell(r.date, false),
      cell(r.description),
      cell(CATEGORY_LABELS[r.category]),
      cell(fmtPlain(r.amount), false),
      cell(r.notes),
    ]);
  }
  return document(out);
}

function expensesFilename(month) {
  return 'expenses-' + month + '.csv'; // month is 'all' or 'YYYY-MM'
}

function reportCsv(rep) {
  const out = [['Month', 'Category', 'This month (OMR)', 'Previous month (OMR)', 'Change (OMR)', 'Change (%)', 'Share (%)']];
  for (const r of [...rep.rows, rep.total]) {
    out.push([
      cell(rep.month, false),
      cell(r.label),
      cell(fmtPlain(r.cur), false),
      cell(fmtPlain(r.prev), false),
      cell(fmtPlain(r.change), false),
      cell(tenthsPlain(r.change_pct), false),
      cell(tenthsPlain(r.share), false),
    ]);
  }
  return document(out);
}

/** Compact JSON with insertion-ordered keys and raw UTF-8, same bytes as Python's json.dumps(separators=(",", ":")). */
const json = (obj) => JSON.stringify(obj);
const money = (minor) => fmtPlain(minor);

function expensesJson(rows, f) {
  const sumMinor = rows.reduce((s, r) => s + r.amount, 0);
  return json({
    currency: CURRENCY,
    filters: { month: f.month, category: f.category, q: f.q, sort: f.sort },
    count: rows.length,
    total: money(sumMinor),
    total_minor: sumMinor,
    expenses: rows.map((r) => ({
      id: r.id,
      date: r.date,
      description: r.description,
      category: r.category,
      category_label: CATEGORY_LABELS[r.category],
      amount: money(r.amount),
      amount_minor: r.amount,
      notes: r.notes,
    })),
  });
}

function summaryJson(s) {
  const [y, m] = dates.parseMonth(s.month);
  const largest = s.largest;
  return json({
    month: s.month,
    label: dates.monthLabel(y, m),
    currency: CURRENCY,
    total: money(s.total),
    total_minor: s.total,
    count: s.count,
    days: s.days,
    daily_average: money(s.average),
    daily_average_minor: s.average,
    largest: largest === null ? null : {
      id: largest.id,
      date: largest.date,
      description: largest.description,
      amount: money(largest.amount),
      amount_minor: largest.amount,
    },
    previous_month: s.prev_month,
    previous_total: money(s.prev_total),
    previous_total_minor: s.prev_total,
    change_pct: s.change === null ? null : tenthsPlain(s.change),
    categories: s.categories.map((c) => ({
      key: c.key,
      label: c.label,
      amount: money(c.amount),
      amount_minor: c.amount,
      share_pct: tenthsPlain(c.share),
    })),
  });
}

module.exports = { BOM, cell, document, expensesCsv, expensesFilename, reportCsv, expensesJson, summaryJson };
