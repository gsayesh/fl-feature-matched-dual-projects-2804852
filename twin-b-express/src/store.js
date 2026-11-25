'use strict';
/**
 * JSON file storage (FR-17). Mirrors twin-a-flask/ledger/store.py.
 *
 * File layout (identical in both builds, so both can even share one file):
 *
 *     {"version": 1, "next_id": 37, "expenses": [{"id", "date", "description",
 *      "category", "amount", "notes"}, ...]}
 *
 * The file is read on every request and written atomically (temp file + rename).
 * Node runs one request at a time on its event loop and every call here is
 * synchronous, so no lock is needed (Twin A uses a threading.Lock instead).
 */

const fs = require('node:fs');
const path = require('node:path');

class Store {
  constructor(file, seedFile) {
    this.file = file;
    this.seedFile = seedFile;
  }

  // -- low level ---------------------------------------------------------

  seed() {
    return JSON.parse(fs.readFileSync(this.seedFile, 'utf8'));
  }

  write(data) {
    fs.mkdirSync(path.dirname(this.file), { recursive: true });
    const tmp = this.file + '.tmp';
    // Same bytes as Python's json.dumps(indent=2, ensure_ascii=False) + "\n".
    fs.writeFileSync(tmp, JSON.stringify(data, null, 2) + '\n', 'utf8');
    fs.renameSync(tmp, this.file); // atomic on POSIX and Windows
  }

  read() {
    if (!fs.existsSync(this.file)) this.write(this.seed()); // first run: start from the sample data
    return JSON.parse(fs.readFileSync(this.file, 'utf8'));
  }

  // -- queries -------------------------------------------------------------

  /** All expenses in entry order (ascending id). */
  expenses() {
    return this.read().expenses.slice();
  }

  get(expenseId) {
    return this.expenses().find((row) => row.id === expenseId) || null;
  }

  // -- commands ------------------------------------------------------------

  /** Append a validated record and return its new id (ids are never reused). */
  add(record) {
    const data = this.read();
    const newId = data.next_id;
    data.expenses.push(row(newId, record));
    data.next_id = newId + 1;
    this.write(data);
    return newId;
  }

  update(expenseId, record) {
    const data = this.read();
    const i = data.expenses.findIndex((r) => r.id === expenseId);
    if (i === -1) return false;
    data.expenses[i] = row(expenseId, record);
    this.write(data);
    return true;
  }

  delete(expenseId) {
    const data = this.read();
    const kept = data.expenses.filter((r) => r.id !== expenseId);
    if (kept.length === data.expenses.length) return false;
    data.expenses = kept;
    this.write(data);
    return true;
  }

  /** FR-16: replace everything with the sample data. */
  reset() {
    this.write(this.seed());
  }

  /** FR-16: delete every expense but keep next_id, so ids are never reused. */
  clear() {
    const data = this.read();
    data.expenses = [];
    this.write(data);
  }
}

/** Fixed key order keeps the file byte-identical between the two builds. */
function row(expenseId, record) {
  return {
    id: expenseId,
    date: record.date,
    description: record.description,
    category: record.category,
    amount: record.amount,
    notes: record.notes,
  };
}

module.exports = { Store };
