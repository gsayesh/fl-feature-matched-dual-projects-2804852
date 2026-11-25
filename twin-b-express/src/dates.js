'use strict';
/**
 * Calendar helpers (FR-17). Mirrors twin-a-flask/ledger/dates.py.
 *
 * Dates are ISO strings (YYYY-MM-DD) throughout. Validation is done by hand rather
 * than by Date/datetime parsing, because those parsers accept different inputs.
 */

const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'];
const MONTH_SHORT = MONTH_NAMES.map((name) => name.slice(0, 3));

const DATE_RE = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;
const MONTH_RE = /^[0-9]{4}-[0-9]{2}$/;
const MIN_YEAR = 2000;
const MAX_YEAR = 2099;

const pad = (n, width = 2) => String(n).padStart(width, '0');

function isLeap(year) {
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

function daysInMonth(year, month) {
  if (month === 2) return isLeap(year) ? 29 : 28;
  return [4, 6, 9, 11].includes(month) ? 30 : 31;
}

/** '2026-11-24' -> [2026, 11, 24]; null when the text is not a real date in 2000-2099. */
function parseDate(value) {
  if (typeof value !== 'string' || !DATE_RE.test(value)) return null;
  const y = Number(value.slice(0, 4));
  const m = Number(value.slice(5, 7));
  const d = Number(value.slice(8, 10));
  if (!(y >= MIN_YEAR && y <= MAX_YEAR && m >= 1 && m <= 12 && d >= 1 && d <= daysInMonth(y, m))) return null;
  return [y, m, d];
}

/** '2026-11' -> [2026, 11]; null when invalid. */
function parseMonth(value) {
  if (typeof value !== 'string' || !MONTH_RE.test(value)) return null;
  const y = Number(value.slice(0, 4));
  const m = Number(value.slice(5, 7));
  if (!(y >= MIN_YEAR && y <= MAX_YEAR && m >= 1 && m <= 12)) return null;
  return [y, m];
}

function monthKey(year, month) {
  return pad(year, 4) + '-' + pad(month);
}

/** Move by delta months, clamped to the supported range. */
function shiftMonth(year, month, delta) {
  let index = year * 12 + (month - 1) + delta;
  index = Math.max(MIN_YEAR * 12, Math.min(MAX_YEAR * 12 + 11, index));
  return [Math.floor(index / 12), (index % 12) + 1];
}

/** [2026, 11] -> 'November 2026'. */
function monthLabel(year, month) {
  return MONTH_NAMES[month - 1] + ' ' + year;
}

/** '2026-11-04' -> '4 Nov 2026'. */
function dateLong(iso) {
  return Number(iso.slice(8, 10)) + ' ' + MONTH_SHORT[Number(iso.slice(5, 7)) - 1] + ' ' + Number(iso.slice(0, 4));
}

/** '2026-11-04' -> '4 Nov'. */
function dateShort(iso) {
  return Number(iso.slice(8, 10)) + ' ' + MONTH_SHORT[Number(iso.slice(5, 7)) - 1];
}

/** Today's local date as ISO. The LEDGER_TODAY setting pins it for tests and parity runs. */
function todayIso(override) {
  if (override && parseDate(override)) return override;
  const now = new Date();
  return pad(now.getFullYear(), 4) + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate());
}

module.exports = {
  MONTH_NAMES, MONTH_SHORT, MIN_YEAR, MAX_YEAR, isLeap, daysInMonth, parseDate, parseMonth,
  monthKey, shiftMonth, monthLabel, dateLong, dateShort, todayIso,
};
