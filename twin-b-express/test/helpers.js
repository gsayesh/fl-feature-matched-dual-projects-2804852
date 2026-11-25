'use strict';
/**
 * Shared helpers for Twin B's tests. Mirrors twin-a-flask/tests/conftest.py.
 *
 * Every test gets its own temporary data file (created from seed.json on first
 * use) and a pinned "today" of 2026-11-25, so results never depend on the clock.
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { createApp } = require('../src/app');

const TODAY = '2026-11-25';

function tempFile() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ledger-b-'));
  return path.join(dir, 'ledger.json');
}

/** Start a fresh app on a free port. Returns { base, close }. */
async function startApp() {
  const app = createApp({ dataFile: tempFile(), today: TODAY });
  const server = await new Promise((resolve) => {
    const s = app.listen(0, '127.0.0.1', () => resolve(s));
  });
  const base = 'http://127.0.0.1:' + server.address().port;
  return { base, close: () => new Promise((resolve) => server.close(resolve)) };
}

/** Send one step of a scenario with the built-in fetch (no redirects followed). */
async function send(base, step) {
  const init = { method: step.method, redirect: 'manual' };
  if (step.method !== 'GET' && step.form) {
    init.body = new URLSearchParams(step.form).toString();
    init.headers = { 'Content-Type': 'application/x-www-form-urlencoded' };
  }
  const res = await fetch(base + step.path, init);
  // Buffer keeps a leading byte-order mark; res.text() would strip it.
  const body = Buffer.from(await res.arrayBuffer()).toString('utf8');
  return { status: res.status, headers: res.headers, body };
}

/** Assert one step's expectations. Same rules as check() in Twin A's tests/test_scenarios.py. */
function check(step, status, headers, body) {
  const exp = step.expect;
  const where = step.method + ' ' + step.path;
  assert.equal(status, exp.status, where);
  if ('location' in exp) assert.equal(headers.get('location'), exp.location, where);
  if ('content_type' in exp) assert.equal(headers.get('content-type'), exp.content_type, where);
  if ('disposition' in exp) assert.equal(headers.get('content-disposition'), exp.disposition, where);
  if (exp.empty_body) assert.equal(body, '', where);
  if ('body' in exp) assert.equal(body, exp.body, where);
  for (const text of exp.contains || []) assert.ok(body.includes(text), where + ': missing ' + JSON.stringify(text));
  for (const text of exp.absent || []) assert.ok(!body.includes(text), where + ': unexpected ' + JSON.stringify(text));
  let pos = 0;
  for (const text of exp.in_order || []) {
    const found = body.indexOf(text, pos);
    assert.ok(found >= 0, where + ': ' + JSON.stringify(text) + ' missing or out of order');
    pos = found + text.length;
  }
}

module.exports = { TODAY, tempFile, startApp, send, check };
