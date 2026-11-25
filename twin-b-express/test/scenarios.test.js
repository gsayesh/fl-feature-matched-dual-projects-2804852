'use strict';
/**
 * Runs the shared conformance fixture (test/scenarios.json) against Twin B.
 *
 * The same file is run by Twin A in tests/test_scenarios.py, so both builds are
 * held to the same requests and the same expected responses. Each scenario is
 * tagged with the requirement IDs it proves (e.g. S11 -> FR-10).
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');

const { startApp, send, check } = require('./helpers');

const FIXTURE = JSON.parse(fs.readFileSync(path.join(__dirname, 'scenarios.json'), 'utf8'));

for (const scenario of FIXTURE.scenarios) {
  test(scenario.id + ' ' + scenario.fr.join(' ') + ' ' + scenario.title, async () => {
    assert.equal(FIXTURE.today, '2026-11-25');
    const app = await startApp();
    try {
      for (const step of scenario.steps) {
        const { status, headers, body } = await send(app.base, step);
        check(step, status, headers, body);
      }
    } finally {
      await app.close();
    }
  });
}
