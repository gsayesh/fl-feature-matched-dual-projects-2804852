"""Expense Ledger, Twin A: Python 3 + Flask + Jinja2.

create_app() is the app factory. Its counterpart in Twin B is createApp() in
twin-b-express/src/app.js.
"""

import mimetypes
import os
from pathlib import Path

from flask import Flask, render_template, request

from . import views
from .store import Store

ROOT = Path(__file__).resolve().parent.parent  # twin-a-flask/
BUILD = "twin-a (Python/Flask)"

mimetypes.add_type("font/woff2", ".woff2")  # same Content-Type for fonts as Express sends


def create_app(settings=None):
    """Build the Flask app.

    settings (all optional, mostly for tests):
      DATA_FILE  path of the JSON store   (env LEDGER_DATA, default data/ledger.json)
      DATA_LABEL text the Data screen shows for it (env LEDGER_DATA_LABEL, default: the path)
      TODAY      pin "today" as YYYY-MM-DD (env LEDGER_TODAY)
    """
    settings = settings or {}
    data_env = os.environ.get("LEDGER_DATA", "")
    data_file = settings.get("DATA_FILE") or data_env or str(ROOT / "data" / "ledger.json")

    app = Flask(__name__, static_folder=None, template_folder=str(ROOT / "templates"))
    app.config.update(
        STORE=Store(data_file, ROOT / "seed.json"),
        DATA_LABEL=settings.get("DATA_LABEL") or os.environ.get("LEDGER_DATA_LABEL", "") or data_env or "data/ledger.json",
        TODAY=settings.get("TODAY") or os.environ.get("LEDGER_TODAY", ""),
        STATIC_DIR=str(ROOT / "static"),
    )
    # Same whitespace rules as the EJS templates in Twin B, so the HTML comes out byte-identical.
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.keep_trailing_newline = True

    from .routes import bp
    app.register_blueprint(bp)

    def error(code):
        html = render_template("error.html", **views.error_page(code))
        return html, code, {"Content-Type": "text/html; charset=utf-8"}

    app.register_error_handler(404, lambda e: error(404))
    app.register_error_handler(405, lambda e: error(405))
    app.register_error_handler(500, lambda e: error(500))

    @app.after_request
    def headers(resp):
        resp.headers["X-Ledger-Build"] = BUILD  # the only intended difference: an HTTP header, never on screen
        if request.endpoint != "ledger.static_files":
            resp.headers["Cache-Control"] = "no-store"
        resp.headers.pop("Allow", None)  # Express sends no Allow header with its 405 page
        return resp

    return app
