"""Walk the same user flows in both twins with a real browser and compare what it shows.

    pip install playwright && python -m playwright install chromium   (one-off, dev only)
    python3 tools/screenshots.py --python twin-a-flask/.venv/bin/python

For every state below the script drives Twin A and Twin B through the same
clicks and form entries, then saves:
  docs/screens/twin-a/<state>.png and docs/screens/twin-b/<state>.png  (1440 x 1000)
  docs/screens/compare.txt   pixel difference and HTML hash for every pair
  demo/twin-a/<state>.html and demo/twin-b/<state>.html  static snapshots for index.html
Both twins start from the sample data with today pinned to 2026-11-25.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parity_check import DATA, TWIN_A, TWIN_B, BUILD, Twin  # noqa: E402

# (state, title, how to reach it). Read-only states first; the data is restored before each write flow.
STATES = [
    ("01-overview", "Overview", {"goto": "/"}),
    ("02-overview-empty-month", "Overview, month without expenses", {"goto": "/?month=2026-08"}),
    ("03-expenses", "Expense list", {"goto": "/expenses"}),
    ("04-expenses-filtered", "List filtered by month and category", {"goto": "/expenses?month=2026-11&category=utilities"}),
    ("05-expenses-no-match", "Search with no results", {"goto": "/expenses?q=souvenir"}),
    ("06-add-form", "Add expense form", {"goto": "/expenses/new"}),
    ("07-add-validation", "Add expense, validation errors", {"goto": "/expenses/new", "fill": {"#f-date": "2026-02-30", "#f-amount": "12.3456", "#f-description": ""}, "submit": "button[type=submit]"}),
    ("08-added-notice", "List after adding an expense", {"reset": True, "goto": "/expenses/new", "fill": {"#f-amount": "3.500", "#f-description": "Taxi to the souq", "#f-category": "transport"}, "submit": "button[type=submit]"}),
    ("09-edit-form", "Edit expense", {"goto": "/expenses/30/edit"}),
    ("10-delete-confirm", "Delete confirmation", {"reset": True, "goto": "/expenses/36/delete"}),
    ("11-deleted-notice", "List after deleting", {"goto": "/expenses/36/delete", "submit": "button[type=submit]", "reset_after": True}),
    ("12-report", "Monthly report", {"goto": "/reports"}),
    ("13-data-tools", "Data tools", {"goto": "/data"}),
    ("14-data-confirm-error", "Data tools, confirmation missing", {"goto": "/data", "submit": ".tool.is-danger button[type=submit]"}),
    ("15-not-found", "404 page", {"goto": "/expenses/999/edit"}),
]


def run_state(page, base, how):
    if how.get("reset"):
        page.request.post(base + "/data/reset", form={"confirm": "yes"})
    response = page.goto(base + how["goto"])
    for selector, value in how.get("fill", {}).items():
        if page.locator(selector).evaluate("el => el.tagName") == "SELECT":
            page.select_option(selector, value)
        else:
            page.fill(selector, value)
    if "submit" in how:
        with page.expect_navigation() as nav:
            page.click(how["submit"])
        response = nav.value
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    return response


def snapshot_html(raw, captured):
    """Make a captured page work as a static file: local assets, links between captured pages."""
    html = raw.replace('href="/static/', 'href="../static/')
    def link(match):
        target = match.group(1).replace("&amp;", "&")
        for state, _, how in STATES:
            if how["goto"] == target and "submit" not in how and state in captured:
                return 'href="{}.html"'.format(state)
        return 'href="#"'
    html = re.sub(r'href="(/[^"]*)"', link, html)
    return re.sub(r'action="/[^"]*"', 'action="#"', html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--node", default="node")
    args = ap.parse_args()
    python = os.path.abspath(args.python) if os.sep in args.python else args.python
    label = {"LEDGER_DATA_LABEL": "data/ledger.json"}  # screens show what a normal run shows
    twins = {"twin-a": Twin("Twin A", [python, "run.py"], TWIN_A, label), "twin-b": Twin("Twin B", [args.node, "server.js"], TWIN_B, label)}
    shots, demo = BUILD / "docs" / "screens", BUILD / "demo"
    for key in twins:
        shutil.rmtree(shots / key, ignore_errors=True)
        shutil.rmtree(demo / key, ignore_errors=True)
        (shots / key).mkdir(parents=True)
        (demo / key).mkdir(parents=True)
    raw = {}
    try:
        for twin in twins.values():
            twin.start()
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")
            for key, twin in twins.items():
                ctx = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
                page = ctx.new_page()
                base = "http://127.0.0.1:{}".format(twin.port)
                for state, _, how in STATES:
                    response = run_state(page, base, how)
                    page.screenshot(path=str(shots / key / (state + ".png")))
                    raw[(key, state)] = (response.status, response.body().decode("utf-8"))
                    if how.get("reset_after"):
                        page.request.post(base + "/data/reset", form={"confirm": "yes"})
                ctx.close()
            browser.close()
    finally:
        for twin in twins.values():
            twin.stop()
        for twin in (TWIN_A, TWIN_B):
            for path in (twin / DATA, twin / (DATA + ".tmp")):
                if path.exists():
                    path.unlink()

    from PIL import Image, ImageChops
    lines = ["Screens captured from both twins with Chrome at 1440 x 1000 (same clicks, same form input).", "",
             "{:<26} {:<34} {:>6} {:>14} {:>14}  {}".format("state", "screen", "status", "html sha256", "pixels diff", "result")]
    states_json, same_all = [], True
    captured = {state for state, _, how in STATES if "submit" not in how}
    for state, title, how in STATES:
        sa, ha = raw[("twin-a", state)]
        sb, hb = raw[("twin-b", state)]
        ia = Image.open(shots / "twin-a" / (state + ".png")).convert("RGB")
        ib = Image.open(shots / "twin-b" / (state + ".png")).convert("RGB")
        diff = ImageChops.difference(ia, ib)
        changed = sum(1 for px in diff.getdata() if px != (0, 0, 0)) if diff.getbbox() else 0
        same = sa == sb and ha == hb and changed == 0
        same_all &= same
        digest = hashlib.sha256(ha.encode("utf-8")).hexdigest()[:12]
        lines.append("{:<26} {:<34} {:>6} {:>14} {:>14}  {}".format(state, title, sa, digest, changed, "identical" if same else "DIFFERENT"))
        for key, body in (("twin-a", ha), ("twin-b", hb)):
            (demo / key / (state + ".html")).write_text(snapshot_html(body, captured), encoding="utf-8")
        states_json.append({"state": state, "title": title, "status": sa, "sha256": hashlib.sha256(ha.encode("utf-8")).hexdigest(),
                            "sha256_b": hashlib.sha256(hb.encode("utf-8")).hexdigest(), "pixels_different": changed})
    lines += ["", "Result: {} of {} screens identical in HTML bytes and in pixels.".format(sum(1 for s in states_json if s["pixels_different"] == 0 and s["sha256"] == s["sha256_b"]), len(STATES))]
    (shots / "compare.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (demo / "states.json").write_text(json.dumps(states_json, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(demo / "static", ignore_errors=True)
    shutil.copytree(TWIN_A / "static", demo / "static")
    print("\n".join(lines))
    return 0 if same_all else 1


if __name__ == "__main__":
    sys.exit(main())
