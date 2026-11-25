"""Pure calculations over the expense list. Mirrors twin-b-express/src/queries.js.

Nothing here touches Flask, so the same rules are easy to unit-test.
All amounts are integers (baisa); percentages are integers in tenths.
"""

from . import dates
from .config import CATEGORIES, CATEGORY_KEYS, DEFAULT_SORT
from .money import div_round
from .text import fold

# FR-04 chart geometry: a fixed SVG viewBox, stretched to the card width by CSS.
CHART_W = 3100
CHART_H = 1000


# ---------------------------------------------------------------- list (FR-06..08)

def filter_rows(rows, month="all", category="all", q=""):
    """FR-07: month, category and text filters combined with AND."""
    needle = fold(q)
    out = []
    for row in rows:
        if month != "all" and not row["date"].startswith(month + "-"):
            continue
        if category != "all" and row["category"] != category:
            continue
        if needle and needle not in fold(row["description"]) and needle not in fold(row["notes"]):
            continue
        out.append(row)
    return out


def sort_rows(rows, sort=DEFAULT_SORT):
    """FR-08: four orders; ties go to the newest id (descending) or oldest id (ascending)."""
    if sort == "date_asc":
        return sorted(rows, key=lambda r: (r["date"], r["id"]))
    if sort == "amount_desc":
        return sorted(rows, key=lambda r: (r["amount"], r["id"]), reverse=True)
    if sort == "amount_asc":
        return sorted(rows, key=lambda r: (r["amount"], r["id"]))
    return sorted(rows, key=lambda r: (r["date"], r["id"]), reverse=True)


def months_present(rows):
    """Distinct 'YYYY-MM' values, newest first (used by the month filter)."""
    return sorted({row["date"][:7] for row in rows}, reverse=True)


def default_month(rows, today):
    """FR-02: the month of the most recent expense, else the current month."""
    if rows:
        return max(row["date"] for row in rows)[:7]
    return today[:7]


def in_month(rows, month):
    return [row for row in rows if row["date"].startswith(month + "-")]


def total(rows):
    return sum(row["amount"] for row in rows)


# ---------------------------------------------------------------- overview (FR-02..05)

def category_totals(rows):
    """{category: baisa} for every category, in the fixed order."""
    totals = {key: 0 for key in CATEGORY_KEYS}
    for row in rows:
        if row["category"] in totals:  # ignore unknown keys in a hand-edited file
            totals[row["category"]] += row["amount"]
    return totals


def month_summary(rows, month, today):
    """Headline figures for one month (FR-02, FR-03, FR-05). Returns raw integers."""
    y, m = dates.parse_month(month)
    current = in_month(rows, month)
    month_total = total(current)
    # Daily average: whole month, or the days elapsed so far in the current month.
    days = dates.days_in_month(y, m)
    if today[:7] == month:
        days = int(today[8:10])
    largest = None
    for row in current:  # entry order, so the first of equal amounts wins
        if largest is None or row["amount"] > largest["amount"]:
            largest = row
    py, pm = dates.shift_month(y, m, -1)
    prev_month = dates.month_key(py, pm)
    prev_total = total(in_month(rows, prev_month))
    change = div_round((month_total - prev_total) * 1000, prev_total) if prev_total > 0 else None
    totals = category_totals(current)
    order = {key: i for i, key in enumerate(CATEGORY_KEYS)}
    cats = [
        {
            "key": key,
            "label": label,
            "amount": totals[key],
            "share": div_round(totals[key] * 1000, month_total) if month_total else 0,
        }
        for key, label in CATEGORIES
        if totals[key] > 0
    ]
    cats.sort(key=lambda c: (-c["amount"], order[c["key"]]))
    latest = sort_rows(current, "date_desc")[:5]
    return {
        "month": month,
        "total": month_total,
        "count": len(current),
        "days": days,
        "average": div_round(month_total, days),
        "largest": largest,
        "prev_month": prev_month,
        "prev_total": prev_total,
        "change": change,
        "categories": cats,
        "latest": latest,
    }


def nice_axis(max_value):
    """FR-04: gridline step of 1, 2 or 5 x 10^n OMR so that at most five lines cover max_value."""
    if max_value <= 0:
        return 10000, 5
    exp = 1000  # 1 OMR in baisa
    while True:
        for mult in (1, 2, 5):
            step = mult * exp
            lines = -(-max_value // step)  # ceiling division
            if lines <= 5:
                return step, lines
        exp *= 10


def running_chart(rows, month, today):
    """FR-04: step paths of the running total for the month and the previous month."""
    y, m = dates.parse_month(month)
    py, pm = dates.shift_month(y, m, -1)
    n, pn = dates.days_in_month(y, m), dates.days_in_month(py, pm)

    def per_day(items, days):
        buckets = [0] * (days + 1)
        for row in items:
            buckets[int(row["date"][8:10])] += row["amount"]
        return buckets

    cur = per_day(in_month(rows, month), n)
    prev = per_day(in_month(rows, dates.month_key(py, pm)), pn)
    end = int(today[8:10]) if today[:7] == month else n  # never draw into the future
    step, lines = nice_axis(max(sum(cur[: end + 1]), sum(prev)))
    top = step * lines

    def x(day, days):
        return div_round(day * CHART_W, days)

    def yv(value):
        return CHART_H - div_round(value * CHART_H, top)

    def path(buckets, days, last):
        parts, running = ["M0 {}".format(CHART_H)], 0
        for day in range(1, last + 1):
            if buckets[day]:
                left = x(day - 1, days)
                parts.append("L{} {}".format(left, yv(running)))
                running += buckets[day]
                parts.append("L{} {}".format(left, yv(running)))
        parts.append("L{} {}".format(x(last, days), yv(running)))
        return " ".join(parts)

    line = path(cur, n, end)
    hits, running = [], 0
    for day in range(1, end + 1):
        running += cur[day]
        iso = "{}-{:02d}".format(month, day)
        hits.append({"x": x(day - 1, n), "w": x(day, n) - x(day - 1, n), "iso": iso, "day": cur[day], "running": running})
    return {
        "line": line,
        "area": "{} L{} {} Z".format(line, x(end, n), CHART_H),
        "prev": path(prev, pn, pn),
        "grid": [{"y": yv(step * i), "value": step * i} for i in range(1, lines + 1)],
        "ticks": [d for d in (1, 8, 15, 22, 29) if d <= n],
        "days": n,
        "hits": hits,
    }


# ---------------------------------------------------------------- report (FR-13)

def report_rows(rows, month):
    """All eight categories with this month, previous month, change and share."""
    y, m = dates.parse_month(month)
    py, pm = dates.shift_month(y, m, -1)
    cur = category_totals(in_month(rows, month))
    prev = category_totals(in_month(rows, dates.month_key(py, pm)))
    cur_total, prev_total = sum(cur.values()), sum(prev.values())

    def line(key, label, a, b, whole):
        return {
            "key": key,
            "label": label,
            "cur": a,
            "prev": b,
            "change": a - b,
            "change_pct": div_round((a - b) * 1000, b) if b > 0 else None,
            "share": div_round(a * 1000, whole) if whole > 0 else None,
        }

    lines = [line(key, label, cur[key], prev[key], cur_total) for key, label in CATEGORIES]
    return {
        "month": month,
        "prev_month": dates.month_key(py, pm),
        "rows": lines,
        "total": line("total", "Total", cur_total, prev_total, cur_total),
    }
