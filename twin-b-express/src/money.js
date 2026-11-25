'use strict';
/**
 * Money rules (FR-10, FR-17). Mirrors twin-a-flask/ledger/money.py.
 *
 * - Amounts are whole baisa (1 OMR = 1000 baisa) stored as integers, never floats.
 * - Rounding is half away from zero, done with integer arithmetic only
 *   (BigInt inside divRound, so even huge totals never touch floating point).
 */

const { MAX_AMOUNT_MINOR, MSG } = require('./config');
const { clean, group } = require('./text');

const AMOUNT_RE = /^[0-9]+(\.[0-9]+)?$/; // [0-9] never matches non-ASCII digits

/** numerator / denominator rounded half away from zero. denominator must be > 0. */
function divRound(numerator, denominator) {
  const n = BigInt(numerator);
  const d = BigInt(denominator);
  const q = (2n * (n < 0n ? -n : n) + d) / (2n * d);
  return Number(n >= 0n ? q : -q);
}

/** Parse user input into baisa. Returns [minor, null] or [null, message]. Rules run in a fixed order. */
function parseAmount(raw) {
  const text = clean(raw).split(',').join('');
  if (text === '') return [null, MSG.amount_required];
  if (!AMOUNT_RE.test(text)) return [null, MSG.amount_format];
  const dot = text.indexOf('.');
  let whole = dot === -1 ? text : text.slice(0, dot);
  let frac = dot === -1 ? '' : text.slice(dot + 1);
  if (frac.length > 3) return [null, MSG.amount_decimals];
  whole = whole.replace(/^0+/, '') || '0';
  frac = (frac + '000').slice(0, 3);
  if (whole === '0' && frac === '000') return [null, MSG.amount_zero];
  if (whole.length > 6) return [null, MSG.amount_max]; // anything over 999,999 OMR is over the limit
  const minor = Number(whole) * 1000 + Number(frac);
  if (minor > MAX_AMOUNT_MINOR) return [null, MSG.amount_max];
  return [minor, null];
}

/** Display form without currency: 1234500 -> '1,234.500'. Negative values use the true minus sign. */
function fmt(minor) {
  const sign = minor < 0 ? '\u2212' : ''; // U+2212 MINUS SIGN
  const abs = Math.abs(minor);
  return sign + group(Math.floor(abs / 1000)) + '.' + String(abs % 1000).padStart(3, '0');
}

/** Display form with currency: 'OMR 1,234.500'. */
function fmtMoney(minor) {
  return 'OMR ' + fmt(minor);
}

/** Display form with an explicit sign: '+12.300', '−4.150', '0.000'. */
function fmtSigned(minor) {
  return (minor > 0 ? '+' : '') + fmt(minor);
}

/** Machine form for CSV/JSON: no grouping, ASCII minus: -4150 -> '-4.150'. */
function fmtPlain(minor) {
  const sign = minor < 0 ? '-' : '';
  const abs = Math.abs(minor);
  return sign + Math.floor(abs / 1000) + '.' + String(abs % 1000).padStart(3, '0');
}

/** Format a value held in tenths of a percent: 543 -> '54.3%', with optional sign. */
function fmtTenths(tenths, signed = false, asciiMinus = false) {
  if (tenths === null) return '\u2014'; // em dash: not applicable
  let sign = '';
  if (tenths < 0) sign = asciiMinus ? '-' : '\u2212';
  else if (tenths > 0 && signed) sign = '+';
  const value = Math.abs(tenths);
  return sign + Math.floor(value / 10) + '.' + (value % 10) + '%';
}

/** Machine form of a percentage for CSV: -65 -> '-6.5', null -> ''. */
function tenthsPlain(tenths) {
  if (tenths === null) return '';
  const sign = tenths < 0 ? '-' : '';
  const value = Math.abs(tenths);
  return sign + Math.floor(value / 10) + '.' + (value % 10);
}

module.exports = { divRound, parseAmount, fmt, fmtMoney, fmtSigned, fmtPlain, fmtTenths, tenthsPlain };
