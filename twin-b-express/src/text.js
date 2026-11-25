'use strict';
/**
 * Text helpers. Mirrors twin-a-flask/ledger/text.py.
 *
 * The two runtimes disagree on what counts as whitespace, how strings are
 * lower-cased and how URLs are encoded, so both builds use these explicit
 * rules instead of library defaults.
 */

// ASCII whitespace only. Python's str.strip() and JavaScript's trim() differ on exotic characters.
const WS = ' \t\n\r\f\v';

// Characters that are never percent-encoded in query strings we generate.
const SAFE = /^[A-Za-z0-9\-_.]$/;

/** Return value trimmed of ASCII whitespace; anything that is not a string becomes ''. */
function clean(value) {
  if (typeof value !== 'string') return '';
  let start = 0;
  let end = value.length;
  while (start < end && WS.includes(value[start])) start += 1;
  while (end > start && WS.includes(value[end - 1])) end -= 1;
  return value.slice(start, end);
}

/** Length in Unicode code points, the same count as Python's len(). */
function charLen(value) {
  return [...value].length;
}

/** Case-fold for search (FR-07): Unicode lower-case, identical to Python's str.lower(). */
function fold(value) {
  return value.toLowerCase();
}

/** Percent-encode one query-string component: space -> '+', everything outside [A-Za-z0-9-_.] -> %XX. */
function encode(value) {
  let out = '';
  for (const ch of value) {
    if (SAFE.test(ch)) out += ch;
    else if (ch === ' ') out += '+';
    else for (const byte of Buffer.from(ch, 'utf8')) out += '%' + byte.toString(16).toUpperCase().padStart(2, '0');
  }
  return out;
}

/** Build '?a=1&b=2' from [key, value] pairs, skipping empty values. Returns '' when nothing is left. */
function query(pairs) {
  const parts = pairs.filter(([, v]) => v !== '').map(([k, v]) => encode(k) + '=' + encode(v));
  return parts.length ? '?' + parts.join('&') : '';
}

/** Thousands separators: 1234567 -> '1,234,567' (never locale-dependent). */
function group(n) {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/** '1 expense' / '13 expenses'. Counts use thousands separators. */
function plural(count, singular, pluralForm) {
  return group(count) + ' ' + (count === 1 ? singular : pluralForm);
}

module.exports = { clean, charLen, fold, encode, query, group, plural };
