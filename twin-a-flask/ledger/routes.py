"""HTTP routes for Twin A (Flask). Mirrors twin-b-express/src/routes.js route for route.

Route map (identical in both builds):
  GET  /                         overview               FR-02..05
  GET  /expenses                 list, filter, sort     FR-06..08
  GET  /expenses/new             add form               FR-09
  POST /expenses                 create                 FR-09, FR-10
  GET  /expenses/<id>/edit       edit form              FR-11
  POST /expenses/<id>            update                 FR-10, FR-11
  GET  /expenses/<id>/delete     confirm delete         FR-12
  POST /expenses/<id>/delete     delete                 FR-12
  GET  /reports                  monthly report         FR-13
  GET  /export/expenses.csv      list export            FR-14
  GET  /export/report.csv        report export          FR-14
  GET  /api/expenses             JSON list              FR-15
  GET  /api/summary              JSON overview          FR-15
  GET  /data                     data tools             FR-16
  POST /data/reset               restore sample data    FR-16
  POST /data/clear               delete everything      FR-16
"""

import re

from flask import Blueprint, Response, current_app, render_template, request, send_from_directory

from . import dates, exports, queries, views
from .config import NOTICES
from .text import clean

bp = Blueprint("ledger", __name__)

_ID_RE = re.compile(r"[1-9][0-9]{0,8}")
# Flask answers OPTIONS automatically; Express does not. Switching it off keeps both builds identical (FR-18).
NO_AUTO = {"provide_automatic_options": False}


# ------------------------------------------------------------------ helpers

def store():
    return current_app.config["STORE"]


def today():
    return dates.today_iso(current_app.config.get("TODAY"))


def arg(name):
    """First value of a query parameter, or '' (Express hands back arrays for repeated keys)."""
    return request.args.get(name, "")


def notice():
    return NOTICES.get(arg("notice"), "")


def page(template, vm, status=200):
    return Response(render_template(template, **vm), status=status, content_type="text/html; charset=utf-8")


def see_other(location):
    """FR-18: 303 See Other with an empty body after every successful POST."""
    return Response(status=303, headers={"Location": location})


def download(body, content_type, filename):
    resp = Response(body, content_type=content_type)
    resp.headers["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
    return resp


def json_response(body):
    return Response(body, content_type="application/json; charset=utf-8")


def parse_id(raw):
    """Ids are positive integers without leading zeros; anything else is a 404 (FR-11)."""
    return int(raw) if _ID_RE.fullmatch(raw or "") else None


def month_or_default(raw, rows):
    """FR-02: a valid ?month=YYYY-MM, else the month of the latest expense."""
    value = clean(raw)
    return value if dates.parse_month(value) else queries.default_month(rows, today())


def not_found():
    return page("error.html", views.error_page(404), 404)


# ------------------------------------------------------------------ static files (FR-01)

@bp.route("/static/<path:filename>", methods=["GET"], **NO_AUTO)
def static_files(filename):
    resp = send_from_directory(current_app.config["STATIC_DIR"], filename, max_age=0)
    # Match Express's static server header for header (found by tools/parity_check.py):
    resp.headers.pop("Content-Disposition", None)  # Werkzeug adds "inline; filename=..."
    if resp.mimetype == "image/svg+xml":
        resp.headers["Content-Type"] = "image/svg+xml"  # no charset parameter on SVG
    return resp


# ------------------------------------------------------------------ overview (FR-02..05)

@bp.route("/", methods=["GET"], **NO_AUTO)
def overview():
    rows = store().expenses()
    month = month_or_default(arg("month"), rows)
    return page("overview.html", views.overview(rows, month, today(), notice()))


# ------------------------------------------------------------------ expenses (FR-06..12)

@bp.route("/expenses", methods=["GET"], **NO_AUTO)
def expense_list():
    f = views.list_filters(request.args)
    return page("expenses.html", views.expense_list(store().expenses(), f, notice()))


@bp.route("/expenses/new", methods=["GET"], **NO_AUTO)
def expense_new():
    values = {"date": today(), "description": "", "category": "", "amount": "", "notes": ""}
    return page("form.html", views.expense_form("add", values, {}))


@bp.route("/expenses", methods=["POST"], **NO_AUTO)
def expense_create():
    values, errors, record = views_validate(request.form)
    if errors:
        return page("form.html", views.expense_form("add", values, errors), 422)
    store().add(record)
    return see_other("/expenses?notice=added")


@bp.route("/expenses/<raw_id>/edit", methods=["GET"], **NO_AUTO)
def expense_edit(raw_id):
    expense_id = parse_id(raw_id)
    row = store().get(expense_id) if expense_id else None
    if row is None:
        return not_found()
    return page("form.html", views.expense_form("edit", views.record_values(row), {}, expense_id))


@bp.route("/expenses/<raw_id>", methods=["POST"], **NO_AUTO)
def expense_update(raw_id):
    expense_id = parse_id(raw_id)
    if expense_id is None or store().get(expense_id) is None:
        return not_found()
    values, errors, record = views_validate(request.form)
    if errors:
        return page("form.html", views.expense_form("edit", values, errors, expense_id), 422)
    store().update(expense_id, record)
    return see_other("/expenses?notice=updated")


@bp.route("/expenses/<raw_id>/delete", methods=["GET"], **NO_AUTO)
def expense_delete_confirm(raw_id):
    expense_id = parse_id(raw_id)
    row = store().get(expense_id) if expense_id else None
    if row is None:
        return not_found()
    return page("delete.html", views.delete_confirm(row))


@bp.route("/expenses/<raw_id>/delete", methods=["POST"], **NO_AUTO)
def expense_delete(raw_id):
    expense_id = parse_id(raw_id)
    if expense_id is None or not store().delete(expense_id):
        return not_found()
    return see_other("/expenses?notice=deleted")


def views_validate(form):
    from .validation import validate_expense
    return validate_expense(form)


# ------------------------------------------------------------------ report (FR-13)

@bp.route("/reports", methods=["GET"], **NO_AUTO)
def report():
    rows = store().expenses()
    month = month_or_default(arg("month"), rows)
    return page("report.html", views.report(rows, month))


# ------------------------------------------------------------------ exports (FR-14)

@bp.route("/export/expenses.csv", methods=["GET"], **NO_AUTO)
def export_expenses():
    f = views.list_filters(request.args)
    rows = queries.sort_rows(queries.filter_rows(store().expenses(), f["month"], f["category"], f["q"]), f["sort"])
    return download(exports.expenses_csv(rows), "text/csv; charset=utf-8", exports.expenses_filename(f["month"]))


@bp.route("/export/report.csv", methods=["GET"], **NO_AUTO)
def export_report():
    rows = store().expenses()
    month = month_or_default(arg("month"), rows)
    body = exports.report_csv(queries.report_rows(rows, month))
    return download(body, "text/csv; charset=utf-8", "report-{}.csv".format(month))


# ------------------------------------------------------------------ JSON API (FR-15)

@bp.route("/api/expenses", methods=["GET"], **NO_AUTO)
def api_expenses():
    f = views.list_filters(request.args)
    rows = queries.sort_rows(queries.filter_rows(store().expenses(), f["month"], f["category"], f["q"]), f["sort"])
    return json_response(exports.expenses_json(rows, f))


@bp.route("/api/summary", methods=["GET"], **NO_AUTO)
def api_summary():
    rows = store().expenses()
    month = month_or_default(arg("month"), rows)
    return json_response(exports.summary_json(queries.month_summary(rows, month, today())))


# ------------------------------------------------------------------ data tools (FR-16)

def data_page(status=200, reset_error="", clear_error="", note=""):
    vm = views.data_tools(store().expenses(), current_app.config["DATA_LABEL"], note, reset_error, clear_error)
    return page("data.html", vm, status)


@bp.route("/data", methods=["GET"], **NO_AUTO)
def data_tools():
    return data_page(note=notice())


@bp.route("/data/reset", methods=["POST"], **NO_AUTO)
def data_reset():
    if request.form.get("confirm", "") != "yes":
        return data_page(422, reset_error=views.MSG["confirm"])
    store().reset()
    return see_other("/data?notice=reset")


@bp.route("/data/clear", methods=["POST"], **NO_AUTO)
def data_clear():
    if request.form.get("confirm", "") != "yes":
        return data_page(422, clear_error=views.MSG["confirm"])
    store().clear()
    return see_other("/data?notice=cleared")
