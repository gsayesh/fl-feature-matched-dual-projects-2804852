"""Money rules (FR-10, FR-17). Mirrors twin-b-express/src/money.js.

* Amounts are whole baisa (1 OMR = 1000 baisa) stored as integers, never floats.
* Rounding is half away from zero, done with integer arithmetic only.
"""

import re

from .config import MAX_AMOUNT_MINOR, MSG
from .text import clean

_AMOUNT_RE = re.compile(r"[0-9]+(\.[0-9]+)?")  # used with fullmatch(); [0-9] never matches non-ASCII digits


def div_round(numerator, denominator):
    """numerator / denominator rounded half away from zero. denominator must be > 0."""
    q = (2 * abs(numerator) + denominator) // (2 * denominator)
    return q if numerator >= 0 else -q


def parse_amount(raw):
    """Parse user input into baisa. Returns (minor, None) or (None, message). Rules run in a fixed order."""
    text = clean(raw).replace(",", "")
    if text == "":
        return None, MSG["amount_required"]
    if not _AMOUNT_RE.fullmatch(text):
        return None, MSG["amount_format"]
    whole, _, frac = text.partition(".")
    if len(frac) > 3:
        return None, MSG["amount_decimals"]
    whole = whole.lstrip("0") or "0"
    frac = (frac + "000")[:3]
    if whole == "0" and frac == "000":
        return None, MSG["amount_zero"]
    if len(whole) > 6:  # anything over 999,999 OMR is over the limit; avoids huge-number maths
        return None, MSG["amount_max"]
    minor = int(whole) * 1000 + int(frac)
    if minor > MAX_AMOUNT_MINOR:
        return None, MSG["amount_max"]
    return minor, None


def _group(n):
    """Thousands separators: 1234567 -> '1,234,567'."""
    return "{:,}".format(n)


def fmt(minor):
    """Display form without currency: 1234500 -> '1,234.500'. Negative values use the true minus sign."""
    sign = "\u2212" if minor < 0 else ""  # U+2212 MINUS SIGN
    whole, frac = divmod(abs(minor), 1000)
    return "{}{}.{:03d}".format(sign, _group(whole), frac)


def fmt_money(minor):
    """Display form with currency: 'OMR 1,234.500'."""
    return "OMR " + fmt(minor)


def fmt_signed(minor):
    """Display form with an explicit sign: '+12.300', '−4.150', '0.000'."""
    return ("+" if minor > 0 else "") + fmt(minor)


def fmt_plain(minor):
    """Machine form for CSV/JSON: no grouping, ASCII minus: -4150 -> '-4.150'."""
    sign = "-" if minor < 0 else ""
    whole, frac = divmod(abs(minor), 1000)
    return "{}{}.{:03d}".format(sign, whole, frac)


def fmt_tenths(tenths, signed=False, ascii_minus=False):
    """Format a value held in tenths of a percent: 543 -> '54.3%', with optional sign."""
    if tenths is None:
        return "\u2014"  # em dash: not applicable
    sign = ""
    if tenths < 0:
        sign = "-" if ascii_minus else "\u2212"
    elif tenths > 0 and signed:
        sign = "+"
    value = abs(tenths)
    return "{}{}.{}%".format(sign, value // 10, value % 10)


def tenths_plain(tenths):
    """Machine form of a percentage for CSV: -65 -> '-6.5', None -> ''."""
    if tenths is None:
        return ""
    sign = "-" if tenths < 0 else ""
    value = abs(tenths)
    return "{}{}.{}".format(sign, value // 10, value % 10)
