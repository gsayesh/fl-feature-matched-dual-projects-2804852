"""Constants for Twin A. Mirrors twin-b-express/src/config.js line for line.

Every user-facing string lives here so both builds show the same wording
(see spec/requirements.json -> "messages").
"""

APP_NAME = "Expense Ledger"
VERSION = "1.0.0"
CURRENCY = "OMR"

# FR-17: categories in their fixed order (also the order of colours and ties).
CATEGORIES = [
    ("housing", "Housing"),
    ("groceries", "Groceries"),
    ("dining", "Dining"),
    ("transport", "Transport"),
    ("utilities", "Utilities"),
    ("health", "Health"),
    ("leisure", "Leisure"),
    ("other", "Other"),
]
CATEGORY_KEYS = [key for key, _ in CATEGORIES]
CATEGORY_LABELS = dict(CATEGORIES)

# FR-08: sort options (value, label); the first one is the default.
SORTS = [
    ("date_desc", "Newest first"),
    ("date_asc", "Oldest first"),
    ("amount_desc", "Amount: high to low"),
    ("amount_asc", "Amount: low to high"),
]
SORT_KEYS = [key for key, _ in SORTS]
# Wording for "Sorted by ..." above the list.
SORT_PHRASES = {
    "date_desc": "newest first",
    "date_asc": "oldest first",
    "amount_desc": "amount, high to low",
    "amount_asc": "amount, low to high",
}
DEFAULT_SORT = "date_desc"

# FR-10: field limits (characters are Unicode code points).
DESCRIPTION_MAX = 80
NOTES_MAX = 200
MAX_AMOUNT_MINOR = 100_000_000  # OMR 100,000.000 expressed in baisa

# FR-10 / FR-16: exact validation messages, in the order the rules run.
MSG = {
    "date_required": "Enter the date of the expense.",
    "date_invalid": "Enter a real date in the format YYYY-MM-DD.",
    "description_required": "Enter a description.",
    "description_long": "Description must be 80 characters or fewer.",
    "category_required": "Choose a category.",
    "amount_required": "Enter an amount.",
    "amount_format": "Amount must be a number, like 12.500.",
    "amount_decimals": "Amount can have at most 3 decimal places.",
    "amount_zero": "Amount must be more than 0.000.",
    "amount_max": "Amount must be 100,000.000 or less.",
    "notes_long": "Notes must be 200 characters or fewer.",
    "summary": "Check the highlighted fields and try again.",
    "confirm": "Tick the box to confirm.",
}

# FR-06 / FR-16: one-line notices shown after a redirect (?notice=<key>).
NOTICES = {
    "added": "Expense added.",
    "updated": "Expense updated.",
    "deleted": "Expense deleted.",
    "reset": "Sample data restored.",
    "cleared": "All expenses deleted.",
}

# Form field order on screen, also the order of the error summary (FR-10).
FIELDS = ["date", "amount", "description", "category", "notes"]
