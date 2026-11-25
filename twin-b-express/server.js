'use strict';
/**
 * Start Twin B:  npm start   (or: node server.js)  ->  http://127.0.0.1:5002
 *
 * Environment (all optional):
 *   PORT          port to listen on (default 5002)
 *   LEDGER_DATA   path of the JSON data file (default data/ledger.json)
 *   LEDGER_DATA_LABEL  text the Data screen shows for that file (default: the path)
 *   LEDGER_TODAY  pin today's date, e.g. 2026-11-25 (used by tests and the parity check)
 */

const { createApp } = require('./src/app');

const port = Number(process.env.PORT || 5002);
createApp().listen(port, '127.0.0.1', () => {
  console.log('Expense Ledger, Twin B (Node/Express): http://127.0.0.1:' + port);
});
