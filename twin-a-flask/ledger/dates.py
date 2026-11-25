"""Calendar helpers (FR-17). Mirrors twin-b-express/src/dates.js.

Dates are ISO strings (YYYY-MM-DD) throughout. Validation is done by hand rather
than by datetime/Date parsing, because those parsers accept different inputs.
"""

import datetime
import re

MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]
MONTH_SHORT = [name[:3] for name in MONTH_NAMES]

_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_MONTH_RE = re.compile(r"[0-9]{4}-[0-9]{2}")
MIN_YEAR, MAX_YEAR = 2000, 2099


def is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year, month):
    if month == 2:
        return 29 if is_leap(year) else 28
    return 30 if month in (4, 6, 9, 11) else 31


def parse_date(value):
    """'2026-11-24' -> (2026, 11, 24); None when the text is not a real date in 2000-2099."""
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        return None
    y, m, d = int(value[0:4]), int(value[5:7]), int(value[8:10])
    if not (MIN_YEAR <= y <= MAX_YEAR and 1 <= m <= 12 and 1 <= d <= days_in_month(y, m)):
        return None
    return y, m, d


def parse_month(value):
    """'2026-11' -> (2026, 11); None when invalid."""
    if not isinstance(value, str) or not _MONTH_RE.fullmatch(value):
        return None
    y, m = int(value[0:4]), int(value[5:7])
    if not (MIN_YEAR <= y <= MAX_YEAR and 1 <= m <= 12):
        return None
    return y, m


def month_key(year, month):
    return "{:04d}-{:02d}".format(year, month)


def shift_month(year, month, delta):
    """Move by delta months, clamped to the supported range."""
    index = year * 12 + (month - 1) + delta
    index = max(MIN_YEAR * 12, min(MAX_YEAR * 12 + 11, index))
    return index // 12, index % 12 + 1


def month_label(year, month):
    """(2026, 11) -> 'November 2026'."""
    return "{} {}".format(MONTH_NAMES[month - 1], year)


def date_long(iso):
    """'2026-11-04' -> '4 Nov 2026'."""
    y, m, d = int(iso[0:4]), int(iso[5:7]), int(iso[8:10])
    return "{} {} {}".format(d, MONTH_SHORT[m - 1], y)


def date_short(iso):
    """'2026-11-04' -> '4 Nov'."""
    m, d = int(iso[5:7]), int(iso[8:10])
    return "{} {}".format(d, MONTH_SHORT[m - 1])


def today_iso(override=None):
    """Today's local date as ISO. The LEDGER_TODAY setting pins it for tests and parity runs."""
    if override and parse_date(override):
        return override
    return datetime.date.today().isoformat()
