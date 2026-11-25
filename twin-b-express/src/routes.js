'use strict';
/**
 * HTTP routes for Twin B (Express). Mirrors twin-a-flask/ledger/routes.py route for route.
 *
 * Route map (identical in both builds):
 *   GET  /                         overview               FR-02..05
 *   GET  /expenses                 list, filter, sort     FR-06..08
 *   GET  /expenses/new             add form               FR-09
 *   POST /expenses                 create                 FR-09, FR-10
 *   GET  /expenses/:id/edit        edit form              FR-11
 *   POST /expenses/:id             update                 FR-10, FR-11
 *   GET  /expenses/:id/delete      confirm delete         FR-12
 *   POST /expenses/:id/delete      delete                 FR-12
 *   GET  /reports                  monthly report         FR-13
 *   GET  /export/expenses.csv      list export            FR-14
 *   GET  /export/report.csv        report export          FR-14
 *   GET  /api/expenses             JSON list              FR-15
 *   GET  /api/summary              JSON overview          FR-15
 *   GET  /data                     data tools             FR-16
 *   POST /data/reset               restore sample data    FR-16
 *   POST /data/clear               delete everything      FR-16
 *
 * Express does not answer "405 Method Not Allowed" on its own (Flask does), so
 * every path ends with an .all() handler that does exactly that (FR-18).
 */

const express = require('express');

const dates = require('./dates');
const exportsOut = require('./exports');
const queries = require('./queries');
const views = require('./views');
const { NOTICES } = require('./config');
const { clean } = require('./text');
const { validateExpense } = require('./validation');

const ID_RE = /^[1-9][0-9]{0,8}$/;

// ------------------------------------------------------------------ helpers

const store = (req) => req.app.locals.store;
const today = (req) => dates.todayIso(req.app.locals.today);

/** First value of a query parameter, or '' (Express hands back arrays for repeated keys). */
const arg = (req, name) => {
  const value = views.firstOf(req.query[name]);
  return typeof value === 'string' ? value : '';
};

/** Known notice keys only; hasOwnProperty keeps keys such as "constructor" out. */
const notice = (req) => {
  const key = arg(req, 'notice');
  return Object.prototype.hasOwnProperty.call(NOTICES, key) ? NOTICES[key] : '';
};

function page(res, template, vm, status = 200) {
  res.status(status).set('Content-Type', 'text/html; charset=utf-8').render(template, vm);
}

/** FR-18: 303 See Other with an empty body after every successful POST. */
function seeOther(res, location) {
  res.status(303).set({ Location: location, 'Content-Type': 'text/html; charset=utf-8' }).end();
}

function download(res, body, contentType, filename) {
  res.set({ 'Content-Type': contentType, 'Content-Disposition': 'attachment; filename="' + filename + '"' }).send(body);
}

function jsonResponse(res, body) {
  res.set('Content-Type', 'application/json; charset=utf-8').send(body);
}

/** Ids are positive integers without leading zeros; anything else is a 404 (FR-11). */
const parseId = (raw) => (ID_RE.test(raw || '') ? Number(raw) : null);

/** FR-02: a valid ?month=YYYY-MM, else the month of the latest expense. */
function monthOrDefault(raw, rows, req) {
  const value = clean(raw);
  return dates.parseMonth(value) ? value : queries.defaultMonth(rows, today(req));
}

const notFound = (res) => page(res, 'error', views.errorPage(404), 404);
const methodNotAllowed = (req, res) => page(res, 'error', views.errorPage(405), 405);

function buildRouter(staticDir) {
  // Same matching rules as Werkzeug: case-sensitive, and "/expenses/" is not "/expenses".
  const router = express.Router({ strict: true, caseSensitive: true });

  // ---------------------------------------------------------------- static files (FR-01)
  router.use('/static', express.static(staticDir, { etag: false, lastModified: true, maxAge: 0, redirect: false, index: false }));
  router.all('/static/*file', (req, res) => (req.method === 'GET' || req.method === 'HEAD' ? notFound(res) : methodNotAllowed(req, res)));

  // ---------------------------------------------------------------- overview (FR-02..05)
  router.get('/', (req, res) => {
    const rows = store(req).expenses();
    const month = monthOrDefault(arg(req, 'month'), rows, req);
    page(res, 'overview', views.overview(rows, month, today(req), notice(req)));
  });
  router.all('/', methodNotAllowed);

  // ---------------------------------------------------------------- expenses (FR-06..12)
  router.get('/expenses', (req, res) => {
    const f = views.listFilters(req.query);
    page(res, 'expenses', views.expenseList(store(req).expenses(), f, notice(req)));
  });

  router.post('/expenses', (req, res) => {
    const { values, errors, record } = validateExpense(req.body);
    if (!record) return page(res, 'form', views.expenseForm('add', values, errors), 422);
    store(req).add(record);
    return seeOther(res, '/expenses?notice=added');
  });
  router.all('/expenses', methodNotAllowed);

  router.get('/expenses/new', (req, res) => {
    const values = { date: today(req), description: '', category: '', amount: '', notes: '' };
    page(res, 'form', views.expenseForm('add', values, {}));
  });

  router.get('/expenses/:rawId/edit', (req, res) => {
    const expenseId = parseId(req.params.rawId);
    const row = expenseId ? store(req).get(expenseId) : null;
    if (!row) return notFound(res);
    return page(res, 'form', views.expenseForm('edit', views.recordValues(row), {}, expenseId));
  });
  router.all('/expenses/:rawId/edit', methodNotAllowed);

  router.get('/expenses/:rawId/delete', (req, res) => {
    const expenseId = parseId(req.params.rawId);
    const row = expenseId ? store(req).get(expenseId) : null;
    if (!row) return notFound(res);
    return page(res, 'delete', views.deleteConfirm(row));
  });

  router.post('/expenses/:rawId/delete', (req, res) => {
    const expenseId = parseId(req.params.rawId);
    if (expenseId === null || !store(req).delete(expenseId)) return notFound(res);
    return seeOther(res, '/expenses?notice=deleted');
  });
  router.all('/expenses/:rawId/delete', methodNotAllowed);

  // "/expenses/new" with POST falls through to here, exactly like Werkzeug: id "new" -> 404.
  router.post('/expenses/:rawId', (req, res) => {
    const expenseId = parseId(req.params.rawId);
    if (expenseId === null || store(req).get(expenseId) === null) return notFound(res);
    const { values, errors, record } = validateExpense(req.body);
    if (!record) return page(res, 'form', views.expenseForm('edit', values, errors, expenseId), 422);
    store(req).update(expenseId, record);
    return seeOther(res, '/expenses?notice=updated');
  });
  router.all('/expenses/:rawId', methodNotAllowed);

  // ---------------------------------------------------------------- report (FR-13)
  router.get('/reports', (req, res) => {
    const rows = store(req).expenses();
    const month = monthOrDefault(arg(req, 'month'), rows, req);
    page(res, 'report', views.report(rows, month));
  });
  router.all('/reports', methodNotAllowed);

  // ---------------------------------------------------------------- exports (FR-14)
  router.get('/export/expenses.csv', (req, res) => {
    const f = views.listFilters(req.query);
    const rows = queries.sortRows(queries.filterRows(store(req).expenses(), f.month, f.category, f.q), f.sort);
    download(res, exportsOut.expensesCsv(rows), 'text/csv; charset=utf-8', exportsOut.expensesFilename(f.month));
  });
  router.all('/export/expenses.csv', methodNotAllowed);

  router.get('/export/report.csv', (req, res) => {
    const rows = store(req).expenses();
    const month = monthOrDefault(arg(req, 'month'), rows, req);
    const body = exportsOut.reportCsv(queries.reportRows(rows, month));
    download(res, body, 'text/csv; charset=utf-8', 'report-' + month + '.csv');
  });
  router.all('/export/report.csv', methodNotAllowed);

  // ---------------------------------------------------------------- JSON API (FR-15)
  router.get('/api/expenses', (req, res) => {
    const f = views.listFilters(req.query);
    const rows = queries.sortRows(queries.filterRows(store(req).expenses(), f.month, f.category, f.q), f.sort);
    jsonResponse(res, exportsOut.expensesJson(rows, f));
  });
  router.all('/api/expenses', methodNotAllowed);

  router.get('/api/summary', (req, res) => {
    const rows = store(req).expenses();
    const month = monthOrDefault(arg(req, 'month'), rows, req);
    jsonResponse(res, exportsOut.summaryJson(queries.monthSummary(rows, month, today(req))));
  });
  router.all('/api/summary', methodNotAllowed);

  // ---------------------------------------------------------------- data tools (FR-16)
  const dataPage = (req, res, status = 200, resetError = '', clearError = '', note = '') => {
    const vm = views.dataTools(store(req).expenses(), req.app.locals.dataLabel, note, resetError, clearError);
    page(res, 'data', vm, status);
  };
  const confirmed = (req) => views.firstOf((req.body || {}).confirm) === 'yes';

  router.get('/data', (req, res) => dataPage(req, res, 200, '', '', notice(req)));
  router.all('/data', methodNotAllowed);

  router.post('/data/reset', (req, res) => {
    if (!confirmed(req)) return dataPage(req, res, 422, views.MSG.confirm, '');
    store(req).reset();
    return seeOther(res, '/data?notice=reset');
  });
  router.all('/data/reset', methodNotAllowed);

  router.post('/data/clear', (req, res) => {
    if (!confirmed(req)) return dataPage(req, res, 422, '', views.MSG.confirm);
    store(req).clear();
    return seeOther(res, '/data?notice=cleared');
  });
  router.all('/data/clear', methodNotAllowed);

  return router;
}

module.exports = { buildRouter, notFound };
