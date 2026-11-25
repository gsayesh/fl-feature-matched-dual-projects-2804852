'use strict';
/**
 * Constants for Twin B. Mirrors twin-a-flask/ledger/config.py line for line.
 *
 * Every user-facing string lives here so both builds show the same wording
 * (see spec/requirements.json -> "messages").
 */

const APP_NAME = 'Expense Ledger';
const VERSION = '1.0.0';
const CURRENCY = 'OMR';

// FR-17: categories in their fixed order (also the order of colours and ties).
const CATEGORIES = [
  ['housing', 'Housing'],
  ['groceries', 'Groceries'],
  ['dining', 'Dining'],
  ['transport', 'Transport'],
  ['utilities', 'Utilities'],
  ['health', 'Health'],
  ['leisure', 'Leisure'],
  ['other', 'Other'],
];
const CATEGORY_KEYS = CATEGORIES.map(([key]) => key);
const CATEGORY_LABELS = Object.fromEntries(CATEGORIES);

// FR-08: sort options [value, label]; the first one is the default.
const SORTS = [
  ['date_desc', 'Newest first'],
  ['date_asc', 'Oldest first'],
  ['amount_desc', 'Amount: high to low'],
  ['amount_asc', 'Amount: low to high'],
];
const SORT_KEYS = SORTS.map(([key]) => key);
// Wording for "Sorted by ..." above the list.
const SORT_PHRASES = {
  date_desc: 'newest first',
  date_asc: 'oldest first',
  amount_desc: 'amount, high to low',
  amount_asc: 'amount, low to high',
};
const DEFAULT_SORT = 'date_desc';

// FR-10: field limits (characters are Unicode code points).
const DESCRIPTION_MAX = 80;
const NOTES_MAX = 200;
const MAX_AMOUNT_MINOR = 100000000; // OMR 100,000.000 expressed in baisa

// FR-10 / FR-16: exact validation messages, in the order the rules run.
const MSG = {
  date_required: 'Enter the date of the expense.',
  date_invalid: 'Enter a real date in the format YYYY-MM-DD.',
  description_required: 'Enter a description.',
  description_long: 'Description must be 80 characters or fewer.',
  category_required: 'Choose a category.',
  amount_required: 'Enter an amount.',
  amount_format: 'Amount must be a number, like 12.500.',
  amount_decimals: 'Amount can have at most 3 decimal places.',
  amount_zero: 'Amount must be more than 0.000.',
  amount_max: 'Amount must be 100,000.000 or less.',
  notes_long: 'Notes must be 200 characters or fewer.',
  summary: 'Check the highlighted fields and try again.',
  confirm: 'Tick the box to confirm.',
};

// FR-06 / FR-16: one-line notices shown after a redirect (?notice=<key>).
const NOTICES = {
  added: 'Expense added.',
  updated: 'Expense updated.',
  deleted: 'Expense deleted.',
  reset: 'Sample data restored.',
  cleared: 'All expenses deleted.',
};

// Form field order on screen, also the order of the error summary (FR-10).
const FIELDS = ['date', 'amount', 'description', 'category', 'notes'];

module.exports = {
  APP_NAME, VERSION, CURRENCY, CATEGORIES, CATEGORY_KEYS, CATEGORY_LABELS,
  SORTS, SORT_KEYS, SORT_PHRASES, DEFAULT_SORT, DESCRIPTION_MAX, NOTES_MAX,
  MAX_AMOUNT_MINOR, MSG, NOTICES, FIELDS,
};
