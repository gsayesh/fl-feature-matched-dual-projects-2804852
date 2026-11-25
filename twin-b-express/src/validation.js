'use strict';
/** Server-side validation for the add/edit form (FR-10). Mirrors twin-a-flask/ledger/validation.py. */

const dates = require('./dates');
const { CATEGORY_KEYS, DESCRIPTION_MAX, MSG, NOTES_MAX } = require('./config');
const { parseAmount } = require('./money');
const { charLen, clean } = require('./text');

/** First value of a form field: urlencoded bodies give an array when a key repeats; Flask takes the first. */
function first(value) {
  return Array.isArray(value) ? value[0] : value;
}

/**
 * Check a submitted form.
 *
 * Returns { values, errors, record }:
 *   values: the trimmed text to show again in the form,
 *   errors: { field: message }, at most one message per field,
 *   record: the clean record ready to save, or null when there are errors.
 */
function validateExpense(form) {
  const values = {};
  for (const field of ['date', 'description', 'category', 'amount', 'notes']) {
    values[field] = clean(first((form || {})[field]));
  }
  const errors = {};

  if (values.date === '') errors.date = MSG.date_required;
  else if (dates.parseDate(values.date) === null) errors.date = MSG.date_invalid;

  if (values.description === '') errors.description = MSG.description_required;
  else if (charLen(values.description) > DESCRIPTION_MAX) errors.description = MSG.description_long;

  if (!CATEGORY_KEYS.includes(values.category)) errors.category = MSG.category_required;

  const [minor, amountError] = parseAmount(values.amount);
  if (amountError) errors.amount = amountError;

  if (charLen(values.notes) > NOTES_MAX) errors.notes = MSG.notes_long;

  if (Object.keys(errors).length) return { values, errors, record: null };
  const record = {
    date: values.date,
    description: values.description,
    category: values.category,
    amount: minor,
    notes: values.notes,
  };
  return { values, errors, record };
}

module.exports = { validateExpense, first };
