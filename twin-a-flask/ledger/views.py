"""View models: plain dicts of ready-to-print strings for the templates.

Mirrors twin-b-express/src/views.js. Both builds work out the same view model,
so the Jinja2 and EJS templates only print strings, with almost no logic. That
is what keeps the HTML byte-identical across the two template engines.
"""

from . import dates, queries
from .config import CATEGORIES, CATEGORY_LABELS, CATEGORY_KEYS, FIELDS, MSG, SORTS, SORT_KEYS, SORT_PHRASES, DEFAULT_SORT, VERSION
from .money import div_round, fmt, fmt_money, fmt_signed, fmt_tenths
from .text import clean, plural, query

SECTIONS = ("overview", "expenses", "add", "reports", "data")


def _pct(tenths):
    """Tenths of a percent -> CSS percentage string, e.g. 564 -> '56.4%'."""
    return "{}.{}%".format(tenths // 10, tenths % 10)


def base(section, title, notice=""):
    """FR-01: data every screen needs (title, active nav link, notice)."""
    return {
        "page_title": title,
        "section": section,
        "nav": {key: (" is-active" if key == section else "") for key in SECTIONS},
        "notice": notice,
        "version": VERSION,
    }


# ------------------------------------------------------------------ FR-02..05

def overview(rows, month, today, notice=""):
    s = queries.month_summary(rows, month, today)
    ch = queries.running_chart(rows, month, today)
    y, m = dates.parse_month(month)
    py, pm = dates.shift_month(y, m, -1)
    ny, nm = dates.shift_month(y, m, 1)
    prev_name = dates.MONTH_NAMES[pm - 1]

    if s["change"] is None:
        delta_text, delta_cls = "No spending in " + prev_name, " is-flat"
    elif s["change"] > 0:
        delta_text, delta_cls = "\u2191 " + fmt_tenths(s["change"]) + " vs " + prev_name, " is-up"
    elif s["change"] < 0:
        delta_text, delta_cls = "\u2193 " + fmt_tenths(-s["change"]) + " vs " + prev_name, " is-down"
    else:
        delta_text, delta_cls = "No change vs " + prev_name, " is-flat"

    largest = s["largest"]
    so_far = " so far" if today[:7] == month else ""
    vm = base("overview", "Overview", notice)
    vm.update({
        "month_label": dates.month_label(y, m),
        "month_name": dates.MONTH_NAMES[m - 1],
        "prev_href": "/" + query([("month", dates.month_key(py, pm))]),
        "prev_label": dates.month_label(py, pm),
        "next_href": "/" + query([("month", dates.month_key(ny, nm))]),
        "next_label": dates.month_label(ny, nm),
        "has_data": s["count"] > 0,
        "total": fmt(s["total"]),
        "delta_text": delta_text,
        "delta_cls": delta_cls,
        "count": "{:,}".format(s["count"]),
        "count_sub": "across " + plural(len(s["categories"]), "category", "categories"),
        "average": fmt(s["average"]),
        "average_sub": "per day over " + plural(s["days"], "day", "days") + so_far,
        "largest": fmt(largest["amount"]) if largest else fmt(0),
        "largest_sub": (largest["description"] + " · " + dates.date_short(largest["date"])) if largest else "No expenses this month",
        "cats": [
            {"key": c["key"], "label": c["label"], "amount": fmt(c["amount"]), "share": _pct(c["share"])}
            for c in s["categories"]
        ],
        "strip": [
            {"key": c["key"], "grow": str(c["amount"]), "title": c["label"] + " · " + _pct(c["share"])}
            for c in sorted(s["categories"], key=lambda c: CATEGORY_KEYS.index(c["key"]))
        ],
        "latest": [
            {
                "date": dates.date_short(r["date"]),
                "description": r["description"],
                "key": r["category"],
                "label": CATEGORY_LABELS[r["category"]],
                "amount": fmt(r["amount"]),
            }
            for r in s["latest"]
        ],
        "latest_href": "/expenses" + query([("month", month)]),
        "add_href": "/expenses/new",
        "chart": {
            "w": queries.CHART_W,
            "h": queries.CHART_H,
            "line": ch["line"],
            "area": ch["area"],
            "prev": ch["prev"],
            "grid": [
                {"y": g["y"], "top": _pct(g["y"]), "label": "{:,}".format(g["value"] // 1000)}
                for g in ch["grid"]
            ],
            "ticks": [
                {
                    "left": _pct(div_round((2 * d - 1) * 1000, 2 * ch["days"])),
                    "label": "{} {}".format(d, dates.MONTH_SHORT[m - 1]) if d == 1 else str(d),
                }
                for d in ch["ticks"]
            ],
            "hits": [
                {
                    "x": h["x"],
                    "w": h["w"],
                    "title": "{} · OMR {} · running total OMR {}".format(dates.date_long(h["iso"]), fmt(h["day"]), fmt(h["running"])),
                }
                for h in ch["hits"]
            ],
            "cur_label": dates.MONTH_NAMES[m - 1],
            "prev_label": prev_name,
            "aria": "Running total of spending in {} compared with {}".format(dates.month_label(y, m), dates.month_label(py, pm)),
        },
    })
    return vm


# ------------------------------------------------------------------ FR-06..08

def list_filters(args):
    """Read and sanitise the list filters from the query string (invalid values fall back to defaults)."""
    month = clean(args.get("month", ""))
    if not dates.parse_month(month):
        month = "all"
    category = clean(args.get("category", ""))
    if category not in CATEGORY_KEYS:
        category = "all"
    q = clean(args.get("q", ""))
    sort = clean(args.get("sort", ""))
    if sort not in SORT_KEYS:
        sort = DEFAULT_SORT
    return {"month": month, "category": category, "q": q, "sort": sort}


def filter_query(f):
    """Only non-default filters go into links, in a fixed order."""
    return query([
        ("month", "" if f["month"] == "all" else f["month"]),
        ("category", "" if f["category"] == "all" else f["category"]),
        ("q", f["q"]),
        ("sort", "" if f["sort"] == DEFAULT_SORT else f["sort"]),
    ])


def _options(pairs, selected):
    return [{"value": v, "label": label, "sel": " selected" if v == selected else ""} for v, label in pairs]


def expense_list(rows, f, notice=""):
    shown = queries.sort_rows(queries.filter_rows(rows, f["month"], f["category"], f["q"]), f["sort"])
    months = queries.months_present(rows)
    if f["month"] != "all" and f["month"] not in months:
        months = sorted(months + [f["month"]], reverse=True)
    month_pairs = [("all", "All months")] + [(mk, dates.month_label(*dates.parse_month(mk))) for mk in months]
    if not rows:
        empty = "none"
    elif not shown:
        empty = "nomatch"
    else:
        empty = ""
    vm = base("expenses", "Expenses", notice)
    vm.update({
        "f": f,
        "month_options": _options(month_pairs, f["month"]),
        "category_options": _options([("all", "All categories")] + CATEGORIES, f["category"]),
        "sort_options": _options(SORTS, f["sort"]),
        "sort_label": SORT_PHRASES[f["sort"]],
        "rows": [
            {
                "id": str(r["id"]),
                "date": dates.date_long(r["date"]),
                "iso": r["date"],
                "description": r["description"],
                "notes": r["notes"],
                "key": r["category"],
                "label": CATEGORY_LABELS[r["category"]],
                "amount": fmt(r["amount"]),
                "edit_href": "/expenses/{}/edit".format(r["id"]),
                "delete_href": "/expenses/{}/delete".format(r["id"]),
            }
            for r in shown
        ],
        "count_text": plural(len(shown), "expense", "expenses"),
        "total_text": fmt_money(queries.total(shown)),
        "export_href": "/export/expenses.csv" + filter_query(f),
        "empty": empty,
        "add_href": "/expenses/new",
    })
    return vm


# ------------------------------------------------------------------ FR-09..12

def expense_form(mode, values, errors, expense_id=None):
    adding = mode == "add"
    vm = base("add" if adding else "expenses", "Add expense" if adding else "Edit expense")
    vm.update({
        "heading": "Add expense" if adding else "Edit expense",
        "eyebrow": "New entry" if adding else "Entry #{}".format(expense_id),
        "lede": "Amounts are in Omani rial (OMR) with up to three decimals.",
        "action": "/expenses" if adding else "/expenses/{}".format(expense_id),
        "submit_label": "Save expense" if adding else "Save changes",
        "v": values,
        "e": {field: errors.get(field, "") for field in FIELDS},
        "err_cls": {field: (" has-error" if field in errors else "") for field in FIELDS},
        "has_errors": bool(errors),
        "summary_title": MSG["summary"],
        "error_list": [{"field": field, "message": errors[field]} for field in FIELDS if field in errors],
        "category_options": _options([("", "Choose a category")] + CATEGORIES, values.get("category", "")),
        "cancel_href": "/expenses",
    })
    return vm


def record_values(row):
    """A saved record as form values (amounts back to '12.500' text)."""
    return {
        "date": row["date"],
        "description": row["description"],
        "category": row["category"],
        "amount": fmt(row["amount"]).replace(",", ""),
        "notes": row["notes"],
    }


def delete_confirm(row):
    vm = base("expenses", "Delete expense")
    vm.update({
        "id": str(row["id"]),
        "description": row["description"],
        "date": dates.date_long(row["date"]),
        "key": row["category"],
        "label": CATEGORY_LABELS[row["category"]],
        "amount": fmt_money(row["amount"]),
        "notes": row["notes"],
        "action": "/expenses/{}/delete".format(row["id"]),
        "cancel_href": "/expenses",
    })
    return vm


# ------------------------------------------------------------------ FR-13

def _trend(change, pct):
    if pct is None:
        return "\u2014", " is-flat"
    if pct > 0:
        return "\u2191 " + fmt_tenths(pct), " is-up"
    if pct < 0:
        return "\u2193 " + fmt_tenths(-pct), " is-down"
    return "0.0%", " is-flat"


def report(rows, month):
    rep = queries.report_rows(rows, month)
    y, m = dates.parse_month(month)
    py, pm = dates.shift_month(y, m, -1)
    ny, nm = dates.shift_month(y, m, 1)

    def line(r):
        trend, trend_cls = _trend(r["change"], r["change_pct"])
        return {
            "key": r["key"],
            "label": r["label"],
            "cur": fmt(r["cur"]),
            "prev": fmt(r["prev"]),
            "change": fmt_signed(r["change"]),
            "trend": trend,
            "trend_cls": trend_cls,
            "share": fmt_tenths(r["share"]),
            "share_w": _pct(r["share"] or 0),
            "zero_cls": " is-zero" if r["cur"] == 0 and r["prev"] == 0 else "",
        }

    vm = base("reports", "Reports")
    vm.update({
        "month_label": dates.month_label(y, m),
        "prev_href": "/reports" + query([("month", dates.month_key(py, pm))]),
        "prev_label": dates.month_label(py, pm),
        "next_href": "/reports" + query([("month", dates.month_key(ny, nm))]),
        "next_label": dates.month_label(ny, nm),
        "cur_head": dates.MONTH_SHORT[m - 1] + " " + str(y),
        "prev_head": dates.MONTH_SHORT[pm - 1] + " " + str(py),
        "rows": [line(r) for r in rep["rows"]],
        "total": line(rep["total"]),
        "export_href": "/export/report.csv" + query([("month", month)]),
    })
    return vm


# ------------------------------------------------------------------ FR-16

def data_tools(rows, data_label, notice="", reset_error="", clear_error=""):
    vm = base("data", "Data", notice)
    if rows:
        first = min(r["date"] for r in rows)
        last = max(r["date"] for r in rows)
        range_text = dates.date_long(first) + " – " + dates.date_long(last)
    else:
        range_text = "No expenses stored"
    vm.update({
        "count_text": plural(len(rows), "expense", "expenses"),
        "range_text": range_text,
        "file_text": data_label,
        "reset_error": reset_error,
        "clear_error": clear_error,
        "export_href": "/export/expenses.csv",
    })
    return vm


# ------------------------------------------------------------------ FR-18

ERRORS = {
    404: ("Page not found", "The page you asked for does not exist. It may have been deleted, or the address may be mistyped."),
    405: ("Method not allowed", "This address exists, but not for that kind of request."),
    500: ("Something went wrong", "The server hit an unexpected error. Nothing was saved."),
}


def error_page(code):
    title, message = ERRORS[code]
    vm = base("", title)
    vm.update({"code": str(code), "title": title, "message": message})
    return vm
