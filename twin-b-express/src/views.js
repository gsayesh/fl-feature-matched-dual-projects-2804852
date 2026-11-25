'use strict';
/**
 * View models: plain objects of ready-to-print strings for the templates.
 *
 * Mirrors twin-a-flask/ledger/views.py. Both builds work out the same view model
 * (same keys, same strings), so the EJS and Jinja2 templates only print values,
 * with almost no logic. That is what keeps the HTML byte-identical across the
 * two template engines. Keys stay snake_case to match the Python side.
 */

const dates = require('./dates');
const queries = require('./queries');
const {
  CATEGORIES, CATEGORY_LABELS, CATEGORY_KEYS, FIELDS, MSG, SORTS, SORT_KEYS, SORT_PHRASES, DEFAULT_SORT, VERSION,
} = require('./config');
const { divRound, fmt, fmtMoney, fmtSigned, fmtTenths } = require('./money');
const { clean, group, plural, query } = require('./text');

const SECTIONS = ['overview', 'expenses', 'add', 'reports', 'data'];

/** Tenths of a percent -> CSS percentage string, e.g. 564 -> '56.4%'. */
function pct(tenths) {
  return Math.floor(tenths / 10) + '.' + (tenths % 10) + '%';
}

/** FR-01: data every screen needs (title, active nav link, notice). */
function base(section, title, notice = '') {
  return {
    page_title: title,
    section,
    nav: Object.fromEntries(SECTIONS.map((key) => [key, key === section ? ' is-active' : ''])),
    notice,
    version: VERSION,
  };
}

// ------------------------------------------------------------------ FR-02..05

function overview(rows, month, today, notice = '') {
  const s = queries.monthSummary(rows, month, today);
  const ch = queries.runningChart(rows, month, today);
  const [y, m] = dates.parseMonth(month);
  const [py, pm] = dates.shiftMonth(y, m, -1);
  const [ny, nm] = dates.shiftMonth(y, m, 1);
  const prevName = dates.MONTH_NAMES[pm - 1];

  let deltaText;
  let deltaCls;
  if (s.change === null) [deltaText, deltaCls] = ['No spending in ' + prevName, ' is-flat'];
  else if (s.change > 0) [deltaText, deltaCls] = ['↑ ' + fmtTenths(s.change) + ' vs ' + prevName, ' is-up'];
  else if (s.change < 0) [deltaText, deltaCls] = ['↓ ' + fmtTenths(-s.change) + ' vs ' + prevName, ' is-down'];
  else [deltaText, deltaCls] = ['No change vs ' + prevName, ' is-flat'];

  const largest = s.largest;
  const soFar = today.slice(0, 7) === month ? ' so far' : '';
  return {
    ...base('overview', 'Overview', notice),
    month_label: dates.monthLabel(y, m),
    month_name: dates.MONTH_NAMES[m - 1],
    prev_href: '/' + query([['month', dates.monthKey(py, pm)]]),
    prev_label: dates.monthLabel(py, pm),
    next_href: '/' + query([['month', dates.monthKey(ny, nm)]]),
    next_label: dates.monthLabel(ny, nm),
    has_data: s.count > 0,
    total: fmt(s.total),
    delta_text: deltaText,
    delta_cls: deltaCls,
    count: group(s.count),
    count_sub: 'across ' + plural(s.categories.length, 'category', 'categories'),
    average: fmt(s.average),
    average_sub: 'per day over ' + plural(s.days, 'day', 'days') + soFar,
    largest: largest ? fmt(largest.amount) : fmt(0),
    largest_sub: largest ? largest.description + ' · ' + dates.dateShort(largest.date) : 'No expenses this month',
    cats: s.categories.map((c) => ({ key: c.key, label: c.label, amount: fmt(c.amount), share: pct(c.share) })),
    strip: s.categories
      .slice()
      .sort((a, b) => CATEGORY_KEYS.indexOf(a.key) - CATEGORY_KEYS.indexOf(b.key))
      .map((c) => ({ key: c.key, grow: String(c.amount), title: c.label + ' · ' + pct(c.share) })),
    latest: s.latest.map((r) => ({
      date: dates.dateShort(r.date),
      description: r.description,
      key: r.category,
      label: CATEGORY_LABELS[r.category],
      amount: fmt(r.amount),
    })),
    latest_href: '/expenses' + query([['month', month]]),
    add_href: '/expenses/new',
    chart: {
      w: queries.CHART_W,
      h: queries.CHART_H,
      line: ch.line,
      area: ch.area,
      prev: ch.prev,
      grid: ch.grid.map((g) => ({ y: g.y, top: pct(g.y), label: group(Math.floor(g.value / 1000)) })),
      ticks: ch.ticks.map((d) => ({
        left: pct(divRound((2 * d - 1) * 1000, 2 * ch.days)),
        label: d === 1 ? d + ' ' + dates.MONTH_SHORT[m - 1] : String(d),
      })),
      hits: ch.hits.map((h) => ({
        x: h.x,
        w: h.w,
        title: dates.dateLong(h.iso) + ' · OMR ' + fmt(h.day) + ' · running total OMR ' + fmt(h.running),
      })),
      cur_label: dates.MONTH_NAMES[m - 1],
      prev_label: prevName,
      aria: 'Running total of spending in ' + dates.monthLabel(y, m) + ' compared with ' + dates.monthLabel(py, pm),
    },
  };
}

// ------------------------------------------------------------------ FR-06..08

/** First value of a query parameter: Express gives an array when a key repeats; Flask takes the first. */
function firstOf(value) {
  return Array.isArray(value) ? value[0] : value;
}

/** Read and sanitise the list filters from the query string (invalid values fall back to defaults). */
function listFilters(args) {
  const get = (name) => clean(firstOf((args || {})[name]));
  let month = get('month');
  if (!dates.parseMonth(month)) month = 'all';
  let category = get('category');
  if (!CATEGORY_KEYS.includes(category)) category = 'all';
  const q = get('q');
  let sort = get('sort');
  if (!SORT_KEYS.includes(sort)) sort = DEFAULT_SORT;
  return { month, category, q, sort };
}

/** Only non-default filters go into links, in a fixed order. */
function filterQuery(f) {
  return query([
    ['month', f.month === 'all' ? '' : f.month],
    ['category', f.category === 'all' ? '' : f.category],
    ['q', f.q],
    ['sort', f.sort === DEFAULT_SORT ? '' : f.sort],
  ]);
}

function options(pairs, selected) {
  return pairs.map(([value, label]) => ({ value, label, sel: value === selected ? ' selected' : '' }));
}

function expenseList(rows, f, notice = '') {
  const shown = queries.sortRows(queries.filterRows(rows, f.month, f.category, f.q), f.sort);
  let months = queries.monthsPresent(rows);
  if (f.month !== 'all' && !months.includes(f.month)) months = [...months, f.month].sort().reverse();
  const monthPairs = [['all', 'All months'], ...months.map((mk) => [mk, dates.monthLabel(...dates.parseMonth(mk))])];
  let empty = '';
  if (!rows.length) empty = 'none';
  else if (!shown.length) empty = 'nomatch';
  return {
    ...base('expenses', 'Expenses', notice),
    f,
    month_options: options(monthPairs, f.month),
    category_options: options([['all', 'All categories'], ...CATEGORIES], f.category),
    sort_options: options(SORTS, f.sort),
    sort_label: SORT_PHRASES[f.sort],
    rows: shown.map((r) => ({
      id: String(r.id),
      date: dates.dateLong(r.date),
      iso: r.date,
      description: r.description,
      notes: r.notes,
      key: r.category,
      label: CATEGORY_LABELS[r.category],
      amount: fmt(r.amount),
      edit_href: '/expenses/' + r.id + '/edit',
      delete_href: '/expenses/' + r.id + '/delete',
    })),
    count_text: plural(shown.length, 'expense', 'expenses'),
    total_text: fmtMoney(queries.total(shown)),
    export_href: '/export/expenses.csv' + filterQuery(f),
    empty,
    add_href: '/expenses/new',
  };
}

// ------------------------------------------------------------------ FR-09..12

function expenseForm(mode, values, errors, expenseId = null) {
  const adding = mode === 'add';
  return {
    ...base(adding ? 'add' : 'expenses', adding ? 'Add expense' : 'Edit expense'),
    heading: adding ? 'Add expense' : 'Edit expense',
    eyebrow: adding ? 'New entry' : 'Entry #' + expenseId,
    lede: 'Amounts are in Omani rial (OMR) with up to three decimals.',
    action: adding ? '/expenses' : '/expenses/' + expenseId,
    submit_label: adding ? 'Save expense' : 'Save changes',
    v: values,
    e: Object.fromEntries(FIELDS.map((field) => [field, errors[field] || ''])),
    err_cls: Object.fromEntries(FIELDS.map((field) => [field, field in errors ? ' has-error' : ''])),
    has_errors: Object.keys(errors).length > 0,
    summary_title: MSG.summary,
    error_list: FIELDS.filter((field) => field in errors).map((field) => ({ field, message: errors[field] })),
    category_options: options([['', 'Choose a category'], ...CATEGORIES], values.category || ''),
    cancel_href: '/expenses',
  };
}

/** A saved record as form values (amounts back to '12.500' text). */
function recordValues(row) {
  return {
    date: row.date,
    description: row.description,
    category: row.category,
    amount: fmt(row.amount).split(',').join(''),
    notes: row.notes,
  };
}

function deleteConfirm(row) {
  return {
    ...base('expenses', 'Delete expense'),
    id: String(row.id),
    description: row.description,
    date: dates.dateLong(row.date),
    key: row.category,
    label: CATEGORY_LABELS[row.category],
    amount: fmtMoney(row.amount),
    notes: row.notes,
    action: '/expenses/' + row.id + '/delete',
    cancel_href: '/expenses',
  };
}

// ------------------------------------------------------------------ FR-13

function trend(change, p) {
  if (p === null) return ['—', ' is-flat'];
  if (p > 0) return ['↑ ' + fmtTenths(p), ' is-up'];
  if (p < 0) return ['↓ ' + fmtTenths(-p), ' is-down'];
  return ['0.0%', ' is-flat'];
}

function report(rows, month) {
  const rep = queries.reportRows(rows, month);
  const [y, m] = dates.parseMonth(month);
  const [py, pm] = dates.shiftMonth(y, m, -1);
  const [ny, nm] = dates.shiftMonth(y, m, 1);

  const line = (r) => {
    const [trendText, trendCls] = trend(r.change, r.change_pct);
    return {
      key: r.key,
      label: r.label,
      cur: fmt(r.cur),
      prev: fmt(r.prev),
      change: fmtSigned(r.change),
      trend: trendText,
      trend_cls: trendCls,
      share: fmtTenths(r.share),
      share_w: pct(r.share || 0),
      zero_cls: r.cur === 0 && r.prev === 0 ? ' is-zero' : '',
    };
  };

  return {
    ...base('reports', 'Reports'),
    month_label: dates.monthLabel(y, m),
    prev_href: '/reports' + query([['month', dates.monthKey(py, pm)]]),
    prev_label: dates.monthLabel(py, pm),
    next_href: '/reports' + query([['month', dates.monthKey(ny, nm)]]),
    next_label: dates.monthLabel(ny, nm),
    cur_head: dates.MONTH_SHORT[m - 1] + ' ' + y,
    prev_head: dates.MONTH_SHORT[pm - 1] + ' ' + py,
    rows: rep.rows.map(line),
    total: line(rep.total),
    export_href: '/export/report.csv' + query([['month', month]]),
  };
}

// ------------------------------------------------------------------ FR-16

function dataTools(rows, dataLabel, notice = '', resetError = '', clearError = '') {
  let rangeText = 'No expenses stored';
  if (rows.length) {
    const sorted = rows.map((r) => r.date).sort();
    rangeText = dates.dateLong(sorted[0]) + ' – ' + dates.dateLong(sorted[sorted.length - 1]);
  }
  return {
    ...base('data', 'Data', notice),
    count_text: plural(rows.length, 'expense', 'expenses'),
    range_text: rangeText,
    file_text: dataLabel,
    reset_error: resetError,
    clear_error: clearError,
    export_href: '/export/expenses.csv',
  };
}

// ------------------------------------------------------------------ FR-18

const ERRORS = {
  404: ['Page not found', 'The page you asked for does not exist. It may have been deleted, or the address may be mistyped.'],
  405: ['Method not allowed', 'This address exists, but not for that kind of request.'],
  500: ['Something went wrong', 'The server hit an unexpected error. Nothing was saved.'],
};

function errorPage(code) {
  const [title, message] = ERRORS[code];
  return { ...base('', title), code: String(code), title, message };
}

module.exports = {
  MSG, base, overview, listFilters, filterQuery, expenseList, expenseForm, recordValues,
  deleteConfirm, report, dataTools, errorPage, firstOf,
};
