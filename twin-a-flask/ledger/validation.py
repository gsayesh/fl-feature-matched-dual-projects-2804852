"""Server-side validation for the add/edit form (FR-10). Mirrors twin-b-express/src/validation.js."""

from . import dates
from .config import CATEGORY_KEYS, DESCRIPTION_MAX, MSG, NOTES_MAX
from .money import parse_amount
from .text import char_len, clean


def validate_expense(form):
    """Check a submitted form.

    Returns (values, errors, record):
      values: the trimmed text to show again in the form,
      errors: {field: message}, at most one message per field,
      record: the clean record ready to save, or None when there are errors.
    """
    values = {field: clean(form.get(field, "")) for field in ("date", "description", "category", "amount", "notes")}
    errors = {}

    if values["date"] == "":
        errors["date"] = MSG["date_required"]
    elif dates.parse_date(values["date"]) is None:
        errors["date"] = MSG["date_invalid"]

    if values["description"] == "":
        errors["description"] = MSG["description_required"]
    elif char_len(values["description"]) > DESCRIPTION_MAX:
        errors["description"] = MSG["description_long"]

    if values["category"] not in CATEGORY_KEYS:
        errors["category"] = MSG["category_required"]

    minor, amount_error = parse_amount(values["amount"])
    if amount_error:
        errors["amount"] = amount_error

    if char_len(values["notes"]) > NOTES_MAX:
        errors["notes"] = MSG["notes_long"]

    if errors:
        return values, errors, None
    record = {
        "date": values["date"],
        "description": values["description"],
        "category": values["category"],
        "amount": minor,
        "notes": values["notes"],
    }
    return values, errors, record
