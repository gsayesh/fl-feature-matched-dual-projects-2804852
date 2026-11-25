'use strict';
/**
 * Expense Ledger, Twin B: Node.js + Express + EJS.
 *
 * createApp() is the app factory. Its counterpart in Twin A is create_app() in
 * twin-a-flask/ledger/__init__.py.
 */

const path = require('node:path');
const express = require('express');

const views = require('./views');
const { Store } = require('./store');
const { buildRouter, notFound } = require('./routes');

const ROOT = path.resolve(__dirname, '..'); // twin-b-express/
const BUILD = 'twin-b (Node/Express)';

/**
 * Build the Express app.
 *
 * settings (all optional, mostly for tests):
 *   dataFile   path of the JSON store    (env LEDGER_DATA, default data/ledger.json)
 *   dataLabel  text the Data screen shows for it (env LEDGER_DATA_LABEL, default: the path)
 *   today      pin "today" as YYYY-MM-DD (env LEDGER_TODAY)
 */
function createApp(settings = {}) {
  const dataEnv = process.env.LEDGER_DATA || '';
  const dataFile = settings.dataFile || dataEnv || path.join(ROOT, 'data', 'ledger.json');

  const app = express();
  app.locals.store = new Store(dataFile, path.join(ROOT, 'seed.json'));
  app.locals.dataLabel = settings.dataLabel || process.env.LEDGER_DATA_LABEL || dataEnv || 'data/ledger.json';
  app.locals.today = settings.today || process.env.LEDGER_TODAY || '';

  app.set('view engine', 'ejs');
  app.set('views', path.join(ROOT, 'views'));
  app.disable('x-powered-by'); // Flask sends no such header
  app.set('etag', false); // nor ETags on pages
  app.set('query parser', 'simple');

  app.use((req, res, next) => {
    res.set('X-Ledger-Build', BUILD); // the only intended difference: an HTTP header, never on screen
    if (!req.path.startsWith('/static/')) res.set('Cache-Control', 'no-store');
    next();
  });
  app.use(express.urlencoded({ extended: false }));
  app.use(buildRouter(path.join(ROOT, 'public')));

  // FR-18: anything that did not match is a 404 page.
  app.use((req, res) => notFound(res));

  // FR-18: unexpected errors render the 500 page (never a stack trace).
  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    console.error(err);
    res.status(500).set('Content-Type', 'text/html; charset=utf-8').render('error', views.errorPage(500));
  });

  return app;
}

module.exports = { createApp, BUILD };
