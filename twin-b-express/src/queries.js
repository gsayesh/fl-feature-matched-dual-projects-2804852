'use strict';
/**
 * Pure calculations over the expense list. Mirrors twin-a-flask/ledger/queries.py.
 *
 * Nothing here touches Express, so the same rules are easy to unit-test.
 * All amounts are integers (baisa); percentages are integers in tenths.
 */

const dates = require('./dates');
const { CATEGORIES, CATEGORY_KEYS, DEFAULT_SORT } = require('./config');
const { divRound } = require('./money');
const { fold } = require('./text');

// FR-04 chart geometry: a fixed SVG viewBox, stretched to the card width by CSS.
const CHART_W = 3100;
const CHART_H = 1000;

// Comparators. Strings here are ASCII dates, so < and > agree with Python's ordering.
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const byDateId = (a, b) => cmp(a.date, b.date) || a.id - b.id;
const byAmountId = (a, b) => a.amount - b.amount || a.id - b.id;

// ---------------------------------------------------------------- list (FR-06..08)

/** FR-07: month, category and text filters combined with AND. */
function filterRows(rows, month = 'all', category = 'all', q = '') {
  const needle = fold(q);
  return rows.filter((row) => {
    if (month !== 'all' && !row.date.startsWith(month + '-')) return false;
    if (category !== 'all' && row.category !== category) return false;
    if (needle && !fold(row.description).includes(needle) && !fold(row.notes).includes(needle)) return false;
    return true;
  });
}

/** FR-08: four orders; ties go to the newest id (descending) or oldest id (ascending). */
function sortRows(rows, sort = DEFAULT_SORT) {
  const copy = rows.slice();
  if (sort === 'date_asc') return copy.sort(byDateId);
  if (sort === 'amount_desc') return copy.sort((a, b) => byAmountId(b, a));
  if (sort === 'amount_asc') return copy.sort(byAmountId);
  return copy.sort((a, b) => byDateId(b, a));
}

/** Distinct 'YYYY-MM' values, newest first (used by the month filter). */
function monthsPresent(rows) {
  return [...new Set(rows.map((row) => row.date.slice(0, 7)))].sort().reverse();
}

/** FR-02: the month of the most recent expense, else the current month. */
function defaultMonth(rows, today) {
  if (rows.length) return rows.map((row) => row.date).sort().pop().slice(0, 7);
  return today.slice(0, 7);
}

function inMonth(rows, month) {
  return rows.filter((row) => row.date.startsWith(month + '-'));
}

function total(rows) {
  return rows.reduce((sum, row) => sum + row.amount, 0);
}

// ---------------------------------------------------------------- overview (FR-02..05)

/** {category: baisa} for every category, in the fixed order. */
function categoryTotals(rows) {
  const totals = Object.fromEntries(CATEGORY_KEYS.map((key) => [key, 0]));
  for (const row of rows) {
    if (Object.prototype.hasOwnProperty.call(totals, row.category)) totals[row.category] += row.amount; // ignore unknown keys
  }
  return totals;
}

/** Headline figures for one month (FR-02, FR-03, FR-05). Returns raw integers. */
function monthSummary(rows, month, today) {
  const [y, m] = dates.parseMonth(month);
  const current = inMonth(rows, month);
  const monthTotal = total(current);
  // Daily average: whole month, or the days elapsed so far in the current month.
  let days = dates.daysInMonth(y, m);
  if (today.slice(0, 7) === month) days = Number(today.slice(8, 10));
  let largest = null;
  for (const row of current) { // entry order, so the first of equal amounts wins
    if (largest === null || row.amount > largest.amount) largest = row;
  }
  const [py, pm] = dates.shiftMonth(y, m, -1);
  const prevMonth = dates.monthKey(py, pm);
  const prevTotal = total(inMonth(rows, prevMonth));
  const change = prevTotal > 0 ? divRound((monthTotal - prevTotal) * 1000, prevTotal) : null;
  const totals = categoryTotals(current);
  const order = Object.fromEntries(CATEGORY_KEYS.map((key, i) => [key, i]));
  const cats = CATEGORIES
    .filter(([key]) => totals[key] > 0)
    .map(([key, label]) => ({
      key,
      label,
      amount: totals[key],
      share: monthTotal ? divRound(totals[key] * 1000, monthTotal) : 0,
    }));
  cats.sort((a, b) => b.amount - a.amount || order[a.key] - order[b.key]);
  const latest = sortRows(current, 'date_desc').slice(0, 5);
  return {
    month,
    total: monthTotal,
    count: current.length,
    days,
    average: divRound(monthTotal, days),
    largest,
    prev_month: prevMonth,
    prev_total: prevTotal,
    change,
    categories: cats,
    latest,
  };
}

/** FR-04: gridline step of 1, 2 or 5 x 10^n OMR so that at most five lines cover maxValue. */
function niceAxis(maxValue) {
  if (maxValue <= 0) return [10000, 5];
  let exp = 1000; // 1 OMR in baisa
  for (;;) {
    for (const mult of [1, 2, 5]) {
      const step = mult * exp;
      const lines = Math.ceil(maxValue / step);
      if (lines <= 5) return [step, lines];
    }
    exp *= 10;
  }
}

const sum = (values) => values.reduce((a, b) => a + b, 0);

/** FR-04: step paths of the running total for the month and the previous month. */
function runningChart(rows, month, today) {
  const [y, m] = dates.parseMonth(month);
  const [py, pm] = dates.shiftMonth(y, m, -1);
  const n = dates.daysInMonth(y, m);
  const pn = dates.daysInMonth(py, pm);

  const perDay = (items, days) => {
    const buckets = new Array(days + 1).fill(0);
    for (const row of items) buckets[Number(row.date.slice(8, 10))] += row.amount;
    return buckets;
  };

  const cur = perDay(inMonth(rows, month), n);
  const prev = perDay(inMonth(rows, dates.monthKey(py, pm)), pn);
  const end = today.slice(0, 7) === month ? Number(today.slice(8, 10)) : n; // never draw into the future
  const [step, lines] = niceAxis(Math.max(sum(cur.slice(0, end + 1)), sum(prev)));
  const top = step * lines;

  const x = (day, days) => divRound(day * CHART_W, days);
  const yv = (value) => CHART_H - divRound(value * CHART_H, top);

  const path = (buckets, days, last) => {
    const parts = ['M0 ' + CHART_H];
    let running = 0;
    for (let day = 1; day <= last; day += 1) {
      if (buckets[day]) {
        const left = x(day - 1, days);
        parts.push('L' + left + ' ' + yv(running));
        running += buckets[day];
        parts.push('L' + left + ' ' + yv(running));
      }
    }
    parts.push('L' + x(last, days) + ' ' + yv(running));
    return parts.join(' ');
  };

  const line = path(cur, n, end);
  const hits = [];
  let running = 0;
  for (let day = 1; day <= end; day += 1) {
    running += cur[day];
    const iso = month + '-' + String(day).padStart(2, '0');
    hits.push({ x: x(day - 1, n), w: x(day, n) - x(day - 1, n), iso, day: cur[day], running });
  }
  const grid = [];
  for (let i = 1; i <= lines; i += 1) grid.push({ y: yv(step * i), value: step * i });
  return {
    line,
    area: line + ' L' + x(end, n) + ' ' + CHART_H + ' Z',
    prev: path(prev, pn, pn),
    grid,
    ticks: [1, 8, 15, 22, 29].filter((d) => d <= n),
    days: n,
    hits,
  };
}

// ---------------------------------------------------------------- report (FR-13)

/** All eight categories with this month, previous month, change and share. */
function reportRows(rows, month) {
  const [y, m] = dates.parseMonth(month);
  const [py, pm] = dates.shiftMonth(y, m, -1);
  const cur = categoryTotals(inMonth(rows, month));
  const prev = categoryTotals(inMonth(rows, dates.monthKey(py, pm)));
  const curTotal = sum(Object.values(cur));
  const prevTotal = sum(Object.values(prev));

  const line = (key, label, a, b, whole) => ({
    key,
    label,
    cur: a,
    prev: b,
    change: a - b,
    change_pct: b > 0 ? divRound((a - b) * 1000, b) : null,
    share: whole > 0 ? divRound(a * 1000, whole) : null,
  });

  return {
    month,
    prev_month: dates.monthKey(py, pm),
    rows: CATEGORIES.map(([key, label]) => line(key, label, cur[key], prev[key], curTotal)),
    total: line('total', 'Total', curTotal, prevTotal, curTotal),
  };
}

module.exports = {
  CHART_W, CHART_H, filterRows, sortRows, monthsPresent, defaultMonth, inMonth, total,
  categoryTotals, monthSummary, niceAxis, runningChart, reportRows,
};
