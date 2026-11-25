"""Parity check: proves Twin A and Twin B answer every request with the same bytes.

    python3 tools/parity_check.py                      start both twins, compare, stop them
    python3 tools/parity_check.py --out docs/parity-report.txt
    python3 tools/parity_check.py --python twin-a-flask/.venv/bin/python

What it does
  1. Starts Twin A (Flask) and Twin B (Express) on free ports, both with
     LEDGER_TODAY=2026-11-25 and a fresh data file created from seed.json.
  2. Crawl: follows every link, stylesheet and form action it finds, starting
     at "/", and requests each URL from both twins (GET).
  3. Flows: replays every step of spec/scenarios.json (adds, edits, deletes,
     validation errors, exports, data tools) against both twins, restoring the
     sample data before each scenario.
  4. Compares, for every request: status code, Location, Content-Type,
     Content-Disposition and the response body, byte for byte.
  5. Finally compares the two JSON data files on disk, byte for byte.

Only the Python standard library is used. Exit code 0 = identical, 1 = any difference.
"""

import argparse
import hashlib
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlsplit

BUILD = Path(__file__).resolve().parent.parent
TWIN_A = BUILD / "twin-a-flask"
TWIN_B = BUILD / "twin-b-express"
DATA = "data/parity.json"  # same relative path in both twins, so the Data screen shows the same text
COMPARED_HEADERS = ("Location", "Content-Type", "Content-Disposition")
MONTH_WINDOW = ("2026-06", "2027-01")  # the crawl follows month links inside this window only


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Twin:
    """One running build."""

    def __init__(self, name, cmd, cwd, extra_env=None):
        self.name, self.cmd, self.cwd = name, cmd, cwd
        self.extra_env = extra_env or {}
        self.port = free_port()
        self.proc = None

    def start(self):
        data = self.cwd / DATA
        for path in (data, data.with_name(data.name + ".tmp")):
            if path.exists():
                path.unlink()
        env = dict(os.environ, PORT=str(self.port), LEDGER_TODAY="2026-11-25", LEDGER_DATA=DATA, **self.extra_env)
        self.proc = subprocess.Popen(self.cmd, cwd=self.cwd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(100):
            try:
                self.request("GET", "/static/favicon.svg")
                return
            except OSError:
                if self.proc.poll() is not None:
                    raise SystemExit("{} did not start:\n{}".format(self.name, self.proc.stderr.read().decode()))
                time.sleep(0.1)
        raise SystemExit("{} did not answer on port {}".format(self.name, self.port))

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(timeout=10)

    def request(self, method, path, form=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        body, headers = None, {}
        if form is not None:
            body = urlencode(form)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, {h: resp.getheader(h) for h in COMPARED_HEADERS + ("X-Ledger-Build",)}, data


class Links(HTMLParser):
    """Collects same-site URLs from href, src and GET form actions."""

    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("href", "src"):
            if a.get(key, "").startswith("/"):
                self.urls.append(a[key])
        if tag == "form" and a.get("method", "get").lower() == "get" and a.get("action", "").startswith("/"):
            self.urls.append(a["action"])


def shown_cmd(cmd):
    """'python run.py' rather than the full interpreter path (keeps local paths out of reports)."""
    return " ".join([Path(cmd[0]).name] + cmd[1:])


def in_window(path):
    query = urlsplit(path).query
    for part in query.split("&"):
        if part.startswith("month=") and len(part) == 13:
            return MONTH_WINDOW[0] <= part[6:] <= MONTH_WINDOW[1]
    return True


class Report:
    def __init__(self):
        self.lines, self.total, self.same = [], 0, 0
        self.builds = set()

    def compare(self, a, b, method, path, form=None, phase=""):
        ra, rb = a.request(method, path, form), b.request(method, path, form)
        self.builds.update({ra[1]["X-Ledger-Build"], rb[1]["X-Ledger-Build"]})
        same = ra[0] == rb[0] and ra[2] == rb[2] and all(ra[1][h] == rb[1][h] for h in COMPARED_HEADERS)
        self.total += 1
        self.same += same
        digest = hashlib.sha256(ra[2]).hexdigest()[:12]
        shown = path if len(path) <= 70 else path[:67] + "..."
        self.lines.append("{:<5} {:<4} {:<6} {:<70} {:>3} {:>7} {}  {}".format(
            self.total, phase, method, shown, ra[0], len(ra[2]), digest, "identical" if same else "DIFFERENT"))
        if not same:
            for label, x, y in (("status", ra[0], rb[0]),) + tuple((h, ra[1][h], rb[1][h]) for h in COMPARED_HEADERS):
                if x != y:
                    self.lines.append("        {}: A={!r} B={!r}".format(label, x, y))
            if ra[2] != rb[2]:
                self.lines.append("        body differs (A {} bytes, B {} bytes)".format(len(ra[2]), len(rb[2])))
        return ra


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--python", default=sys.executable, help="Python with Flask installed (default: this one)")
    ap.add_argument("--node", default="node", help="Node.js binary (default: node)")
    ap.add_argument("--out", help="also write the report to this file")
    ap.add_argument("--max-pages", type=int, default=400)
    args = ap.parse_args()

    if not (TWIN_B / "node_modules").exists():
        raise SystemExit("Twin B has no node_modules: run `npm install` in twin-b-express first")
    # Relative paths are resolved here, because each twin starts in its own folder.
    python = os.path.abspath(args.python) if os.sep in args.python else args.python  # abspath: keep venv symlinks
    a = Twin("Twin A", [python, "run.py"], TWIN_A)
    b = Twin("Twin B", [args.node, "server.js"], TWIN_B)
    report = Report()
    started = time.time()
    try:
        a.start()
        b.start()

        # ---- 1. crawl every reachable page
        seen, queue, crawled = set(), ["/"], 0
        while queue and crawled < args.max_pages:
            path = queue.pop(0)
            if path in seen or not in_window(path):
                continue
            seen.add(path)
            status, headers, body = report.compare(a, b, "GET", path, phase="crawl")
            crawled += 1
            if (headers["Content-Type"] or "").startswith("text/html"):
                parser = Links()
                parser.feed(body.decode("utf-8"))
                queue.extend(u for u in parser.urls if u not in seen)

        # ---- 2. replay every scenario step (writes included)
        fixture = json.loads((BUILD / "spec" / "scenarios.json").read_text(encoding="utf-8"))
        for scenario in fixture["scenarios"]:
            report.compare(a, b, "POST", "/data/reset", {"confirm": "yes"}, phase=scenario["id"])
            for step in scenario["steps"]:
                form = step.get("form")
                if step["method"] != "GET" and form is None:
                    form = {}
                report.compare(a, b, step["method"], step["path"], form if step["method"] != "GET" else None, phase=scenario["id"])

        # ---- 3. the files on disk must match too
        file_a, file_b = (TWIN_A / DATA).read_bytes(), (TWIN_B / DATA).read_bytes()
        files_same = file_a == file_b
    finally:
        a.stop()
        b.stop()
        for twin in (TWIN_A, TWIN_B):
            for path in (twin / DATA, twin / (DATA + ".tmp")):
                if path.exists():
                    path.unlink()

    header = [
        "Expense Ledger parity check",
        "Twin A: {} (port {})   Twin B: {} (port {})".format(shown_cmd(a.cmd), a.port, shown_cmd(b.cmd), b.port),
        "Builds that answered (X-Ledger-Build header): {}".format(", ".join(sorted(x for x in report.builds if x))),
        "Compared per request: status, Location, Content-Type, Content-Disposition and the body, byte for byte.",
        "",
        "{:<5} {:<4} {:<6} {:<70} {:>3} {:>7} {}".format("#", "via", "method", "path", "st", "bytes", "sha256"),
    ]
    summary = [
        "",
        "Pages crawled: {}   Scenario steps replayed: {}".format(crawled, report.total - crawled),
        "Requests compared: {}   identical: {}   different: {}".format(report.total, report.same, report.total - report.same),
        "Data files after the run (data/parity.json): {}".format("byte-identical" if files_same else "DIFFERENT"),
        "Result: {}   ({:.1f} s)".format("PASS, the twins are indistinguishable" if report.same == report.total and files_same else "FAIL", time.time() - started),
    ]
    text = "\n".join(header + report.lines + summary) + "\n"
    print(text if len(report.lines) < 60 else "\n".join(header[:4] + summary))
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0 if report.same == report.total and files_same else 1


if __name__ == "__main__":
    sys.exit(main())
