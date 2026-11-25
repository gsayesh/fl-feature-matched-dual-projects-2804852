"""CSV and JSON outputs (FR-14, FR-15). Mirrors twin-b-express/src/exports.js.

The CSV writer is hand-rolled (not the csv module) so its quoting rules match
Twin B exactly: RFC 4180, CRLF, UTF-8 with BOM, formula-injection guard.
"""

import json

from . import dates
from .config import CATEGORY_LABELS, CURRENCY
from .money import fmt_plain, tenths_plain

BOM = "\ufeff"  # UTF-8 byte-order mark so Excel detects UTF-8 (Arabic text)
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def cell(value, text=True):
    """One CSV cell. Text cells starting with a formula character get a leading apostrophe."""
    s = str(value)
    if text and s.startswith(_FORMULA_START):
        s = "'" + s
    if any(ch in s for ch in (",", '"', "\r", "\n")):
        s = '"' + s.replace('"', '""') + '"'
    return s


def document(rows):
    """rows: list of lists of already-converted cells."""
    return BOM + "".join(",".join(row) + "\r\n" for row in rows)


def expenses_csv(rows):
    out = [["ID", "Date", "Description", "Category", "Amount (OMR)", "Notes"]]
    for r in rows:
        out.append([
            cell(r["id"], text=False),
            cell(r["date"], text=False),
            cell(r["description"]),
            cell(CATEGORY_LABELS[r["category"]]),
            cell(fmt_plain(r["amount"]), text=False),
            cell(r["notes"]),
        ])
    return document(out)


def expenses_filename(month):
    return "expenses-{}.csv".format(month)  # month is 'all' or 'YYYY-MM'


def report_csv(rep):
    out = [["Month", "Category", "This month (OMR)", "Previous month (OMR)", "Change (OMR)", "Change (%)", "Share (%)"]]
    for r in rep["rows"] + [rep["total"]]:
        out.append([
            cell(rep["month"], text=False),
            cell(r["label"]),
            cell(fmt_plain(r["cur"]), text=False),
            cell(fmt_plain(r["prev"]), text=False),
            cell(fmt_plain(r["change"]), text=False),
            cell(tenths_plain(r["change_pct"]), text=False),
            cell(tenths_plain(r["share"]), text=False),
        ])
    return document(out)


def _json(obj):
    """Compact JSON with insertion-ordered keys and raw UTF-8, same bytes as JSON.stringify()."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _money(minor):
    return fmt_plain(minor)


def expenses_json(rows, f):
    return _json({
        "currency": CURRENCY,
        "filters": {"month": f["month"], "category": f["category"], "q": f["q"], "sort": f["sort"]},
        "count": len(rows),
        "total": _money(sum(r["amount"] for r in rows)),
        "total_minor": sum(r["amount"] for r in rows),
        "expenses": [
            {
                "id": r["id"],
                "date": r["date"],
                "description": r["description"],
                "category": r["category"],
                "category_label": CATEGORY_LABELS[r["category"]],
                "amount": _money(r["amount"]),
                "amount_minor": r["amount"],
                "notes": r["notes"],
            }
            for r in rows
        ],
    })


def summary_json(s):
    y, m = dates.parse_month(s["month"])
    largest = s["largest"]
    return _json({
        "month": s["month"],
        "label": dates.month_label(y, m),
        "currency": CURRENCY,
        "total": _money(s["total"]),
        "total_minor": s["total"],
        "count": s["count"],
        "days": s["days"],
        "daily_average": _money(s["average"]),
        "daily_average_minor": s["average"],
        "largest": None if largest is None else {
            "id": largest["id"],
            "date": largest["date"],
            "description": largest["description"],
            "amount": _money(largest["amount"]),
            "amount_minor": largest["amount"],
        },
        "previous_month": s["prev_month"],
        "previous_total": _money(s["prev_total"]),
        "previous_total_minor": s["prev_total"],
        "change_pct": None if s["change"] is None else tenths_plain(s["change"]),
        "categories": [
            {
                "key": c["key"],
                "label": c["label"],
                "amount": _money(c["amount"]),
                "amount_minor": c["amount"],
                "share_pct": tenths_plain(c["share"]),
            }
            for c in s["categories"]
        ],
    })
