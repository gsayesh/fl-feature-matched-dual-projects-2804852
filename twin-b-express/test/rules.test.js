'use strict';
/**
 * Unit tests for the rules behind the screens. Mirrors Twin A's tests/test_rules.py.
 *
 * Naming: "FR-NN <what it proves>". Twin A has a test with the same words,
 * written test_frNN_<what_it_proves>, so tools/trace.py can pair them one to one.
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');

const dates = require('../src/dates');
const exportsOut = require('../src/exports');
const queries = require('../src/queries');
const { MSG } = require('../src/config');
const { divRound, fmt, fmtMoney, fmtPlain, fmtSigned, parseAmount } = require('../src/money');
const { Store } = require('../src/store');
const { encode, query } = require('../src/text');
const { validateExpense } = require('../src/validation');
const { TODAY, tempFile, startApp } = require('./helpers');

const ROOT = path.resolve(__dirname, '..');
const SEED = JSON.parse(fs.readFileSync(path.join(ROOT, 'seed.json'), 'utf8')).expenses;

const form = (kw = {}) => ({ date: '2026-11-25', description: 'Test entry', category: 'other', amount: '1.000', notes: '', ...kw });
const ids = (rows) => rows.map((r) => r.id);

// ------------------------------------------------------------------ FR-17 money and dates

test('FR-17 div round rounds half away from zero', () => {
  assert.equal(divRound(5, 10), 1); // 0.5 -> 1
  assert.equal(divRound(15, 10), 2); // 1.5 -> 2
  assert.equal(divRound(25, 10), 3); // 2.5 -> 3 (banker's rounding would give 2)
  assert.equal(divRound(4, 10), 0);
  assert.equal(divRound(-5, 10), -1);
  assert.equal(divRound(-15, 10), -2);
  assert.equal(divRound(14, 28), 1);
  assert.equal(divRound(10n ** 20n + 1n, 2), Number(5n * 10n ** 19n + 1n)); // BigInt inside: exact far beyond 2**53
});

test('FR-17 amounts format with three decimals', () => {
  assert.equal(fmt(1234500), '1,234.500');
  assert.equal(fmt(0), '0.000');
  assert.equal(fmt(-4150), '−4.150');
  assert.equal(fmtMoney(6200), 'OMR 6.200');
  assert.equal(fmtSigned(12300), '+12.300');
  assert.equal(fmtPlain(-4150), '-4.150');
  assert.equal(fmtPlain(1234500), '1234.500');
});

test('FR-17 dates use iso and short month names', () => {
  assert.equal(dates.dateLong('2026-11-04'), '4 Nov 2026');
  assert.equal(dates.dateShort('2026-11-04'), '4 Nov');
  assert.equal(dates.monthLabel(2026, 11), 'November 2026');
  assert.equal(dates.todayIso('2026-11-25'), '2026-11-25');
});

test('FR-17 leap years and month lengths', () => {
  assert.equal(dates.daysInMonth(2028, 2), 29);
  assert.equal(dates.daysInMonth(2026, 2), 28);
  assert.ok(dates.isLeap(2000) && !dates.isLeap(2100));
  assert.equal(dates.parseDate('2026-02-29'), null);
  assert.deepEqual(dates.parseDate('2028-02-29'), [2028, 2, 29]);
  assert.equal(dates.parseDate('1999-12-31'), null);
  assert.equal(dates.parseDate('2026-1-05'), null);
  assert.equal(dates.parseDate('2026-11-31'), null);
});

test('FR-17 shift month wraps years', () => {
  assert.deepEqual(dates.shiftMonth(2026, 1, -1), [2025, 12]);
  assert.deepEqual(dates.shiftMonth(2026, 12, 1), [2027, 1]);
  assert.deepEqual(dates.shiftMonth(2000, 1, -1), [2000, 1]);
  assert.deepEqual(dates.shiftMonth(2099, 12, 1), [2099, 12]);
});

// ------------------------------------------------------------------ FR-10 validation

test('FR-10 amount parsing accepts plain numbers', () => {
  assert.deepEqual(parseAmount('12.5'), [12500, null]);
  assert.deepEqual(parseAmount('1,250.5'), [1250500, null]);
  assert.deepEqual(parseAmount('0.001'), [1, null]);
  assert.deepEqual(parseAmount('100000'), [100000000, null]);
  assert.deepEqual(parseAmount(' 7 '), [7000, null]);
  assert.deepEqual(parseAmount('007.10'), [7100, null]);
});

test('FR-10 amount parsing rejects bad input in rule order', () => {
  const cases = {
    '': 'amount_required',
    abc: 'amount_format',
    '1.2.3': 'amount_format',
    '-5': 'amount_format',
    '1e3': 'amount_format',
    '.5': 'amount_format',
    '5.': 'amount_format',
    '١٢': 'amount_format', // Arabic-Indic digits are not accepted
    '1.2345': 'amount_decimals',
    '0': 'amount_zero',
    '0.000': 'amount_zero',
    '100000.001': 'amount_max',
    '9999999': 'amount_max',
  };
  for (const [raw, key] of Object.entries(cases)) assert.deepEqual(parseAmount(raw), [null, MSG[key]], raw);
});

test('FR-10 text limits count characters not bytes', () => {
  assert.deepEqual(validateExpense(form({ description: 'ب'.repeat(80) })).errors, {});
  assert.deepEqual(validateExpense(form({ description: '\u{1F600}'.repeat(80) })).errors, {}); // 80 characters, 160 UTF-16 units
  assert.deepEqual(validateExpense(form({ description: 'ب'.repeat(81) })).errors, { description: MSG.description_long });
  assert.deepEqual(validateExpense(form({ notes: 'n'.repeat(200) })).errors, {});
  assert.deepEqual(validateExpense(form({ notes: 'n'.repeat(201) })).errors, { notes: MSG.notes_long });
});

test('FR-10 validation trims ascii whitespace only', () => {
  assert.equal(validateExpense(form({ description: '  Rent\t' })).record.description, 'Rent');
  assert.equal(validateExpense(form({ description: '\u00a0Rent\u00a0' })).record.description, '\u00a0Rent\u00a0'); // no-break spaces are kept
  assert.deepEqual(validateExpense(form({ description: '   ' })).errors, { description: MSG.description_required });
});

// ------------------------------------------------------------------ FR-07 / FR-08 list rules

test('FR-07 search ignores case and matches notes', () => {
  assert.deepEqual(ids(queries.filterRows(SEED, 'all', 'all', 'AL KHUWAIR')), [1, 13, 24]);
  assert.equal(queries.filterRows(SEED, '2026-11', 'utilities').length, 3);
});

test('FR-07 query strings are encoded the same way', () => {
  assert.equal(query([['q', 'Al Khuwair & co'], ['month', '']]), '?q=Al+Khuwair+%26+co');
  assert.equal(encode('أكتوبر'), '%D8%A3%D9%83%D8%AA%D9%88%D8%A8%D8%B1');
  assert.equal(query([]), '');
});

test('FR-08 sort ties break on entry number', () => {
  const rows = [
    { id: 1, date: '2026-11-01', amount: 500 },
    { id: 2, date: '2026-11-01', amount: 500 },
    { id: 3, date: '2026-10-01', amount: 900 },
  ];
  assert.deepEqual(ids(queries.sortRows(rows, 'date_desc')), [2, 1, 3]);
  assert.deepEqual(ids(queries.sortRows(rows, 'date_asc')), [3, 1, 2]);
  assert.deepEqual(ids(queries.sortRows(rows, 'amount_desc')), [3, 2, 1]);
  assert.deepEqual(ids(queries.sortRows(rows, 'amount_asc')), [1, 2, 3]);
});

// ------------------------------------------------------------------ FR-02..04, FR-13 figures

test('FR-02 month summary matches hand calculation', () => {
  const s = queries.monthSummary(SEED, '2026-11', TODAY);
  assert.deepEqual([s.total, s.count, s.days, s.average], [496850, 13, 25, 19874]);
  assert.equal(s.change, -65); // tenths of a percent: -6.5 %
  assert.equal(s.largest.id, 24);
  assert.deepEqual(s.categories.slice(0, 3).map((c) => c.key), ['housing', 'groceries', 'utilities']);
});

test('FR-04 axis steps are 1 2 or 5 times a power of ten', () => {
  assert.deepEqual(queries.niceAxis(531550), [200000, 3]);
  assert.deepEqual(queries.niceAxis(4000), [1000, 4]);
  assert.deepEqual(queries.niceAxis(9999), [2000, 5]);
  assert.deepEqual(queries.niceAxis(1), [1000, 1]);
  assert.deepEqual(queries.niceAxis(0), [10000, 5]);
});

test('FR-13 report change is empty without previous spending', () => {
  const rep = queries.reportRows(SEED, '2026-09');
  assert.ok(rep.rows.every((r) => r.change_pct === null));
  assert.equal(rep.rows[0].share, 546); // housing: 280.000 of 512.400 = 54.6 %
  assert.equal(rep.total.cur, 512400);
});

// ------------------------------------------------------------------ FR-14 / FR-15 outputs

test('FR-14 csv cells guard formulas and quote specials', () => {
  assert.equal(exportsOut.cell('=1+1'), "'=1+1");
  assert.equal(exportsOut.cell('-5'), "'-5");
  assert.equal(exportsOut.cell('@home'), "'@home");
  assert.equal(exportsOut.cell('a,b'), '"a,b"');
  assert.equal(exportsOut.cell('say "hi"'), '"say ""hi"""');
  assert.equal(exportsOut.cell('x\ny'), '"x\ny"');
  assert.equal(exportsOut.cell('-4.150', false), '-4.150');
});

test('FR-15 json is compact with stable key order', () => {
  const f = { month: 'all', category: 'all', q: '', sort: 'date_desc' };
  const body = exportsOut.expensesJson(SEED.slice(0, 1), f);
  assert.ok(body.startsWith('{"currency":"OMR","filters":{"month":"all","category":"all","q":"","sort":"date_desc"},"count":1,'));
  assert.ok(body.includes('"amount":"280.000","amount_minor":280000'));
});

// ------------------------------------------------------------------ FR-17 storage

test('FR-17 store creates file from seed and never reuses ids', () => {
  const store = new Store(tempFile(), path.join(ROOT, 'seed.json'));
  assert.equal(store.expenses().length, 36);
  const record = { date: '2026-11-25', description: 'x', category: 'other', amount: 1000, notes: '' };
  assert.equal(store.add(record), 37);
  assert.equal(store.delete(37), true);
  assert.equal(store.add(record), 38);
  store.clear();
  assert.deepEqual(store.expenses(), []);
  assert.equal(store.add(record), 39);
  store.reset();
  assert.ok(store.expenses().length === 36 && store.add(record) === 37);
});

test('FR-17 store file format is stable', () => {
  const file = tempFile();
  const store = new Store(file, path.join(ROOT, 'seed.json'));
  store.add({ date: '2026-11-25', description: 'Karak', category: 'dining', amount: 300, notes: '' });
  const text = fs.readFileSync(file, 'utf8');
  assert.ok(text.startsWith('{\n  "version": 1,\n  "next_id": 38,\n  "expenses": [\n'));
  assert.ok(text.includes('"id": 37,\n      "date": "2026-11-25",\n      "description": "Karak",'));
  assert.ok(text.includes('فاتورة')); // Arabic kept as UTF-8, not \u escapes
  assert.ok(text.endsWith('}\n'));
});

// ------------------------------------------------------------------ FR-01 / FR-18 shell and errors

test('FR-01 every screen shares the shell', async () => {
  const app = await startApp();
  try {
    for (const [p, section] of [['/', '/'], ['/expenses', '/expenses'], ['/expenses/new', '/expenses/new'], ['/reports', '/reports'], ['/data', '/data']]) {
      const body = await (await fetch(app.base + p)).text();
      assert.equal(body.split('class="nav-link').length - 1, 5, p);
      assert.ok(body.includes('href="' + section + '" aria-current="page">'), p);
      assert.ok(body.includes('Expense Ledger 1.0.0 · Amounts in Omani rial (OMR)'), p);
    }
  } finally {
    await app.close();
  }
});

test('FR-18 unknown method returns 405 page', async () => {
  const app = await startApp();
  try {
    const res = await fetch(app.base + '/reports', { method: 'DELETE' });
    assert.equal(res.status, 405);
    assert.ok((await res.text()).includes('<h1>Method not allowed</h1>'));
  } finally {
    await app.close();
  }
});
