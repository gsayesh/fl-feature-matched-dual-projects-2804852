"""Build the requirements write-up and the traceability matrix.

    python3 tools/trace.py                     write docs/REQUIREMENTS.md from the sources
    python3 tools/trace.py --run --python twin-a-flask/.venv/bin/python
                                               also run both test suites and record the results

Sources (nothing in the matrix is typed by hand):
  spec/requirements.json           the requirements (FR-01 ... FR-18) and every message
  spec/scenarios.json              the shared scenarios, each tagged with FR IDs
  "FR-xx" comments in the code     where each requirement is implemented, per twin
  test names in both suites        test_frNN_... (pytest) and "FR-NN ..." (node:test)
Outputs: docs/REQUIREMENTS.md, docs/traceability.json and, with --run,
docs/test-output-twin-a.txt and docs/test-output-twin-b.txt.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent
A, B = BUILD / "twin-a-flask", BUILD / "twin-b-express"
A_CODE = sorted(list((A / "ledger").glob("*.py")) + list((A / "templates").glob("*.html")) + [A / "run.py"])
B_CODE = sorted(list((B / "src").glob("*.js")) + list((B / "views").glob("*.ejs")) + [B / "server.js"])

FR_RANGE = re.compile(r"FR-(\d\d)\.\.(\d\d)")
FR_ONE = re.compile(r"FR-(\d\d)")


def fr_ids(text):
    """Every FR id mentioned in text, with ranges such as FR-02..05 expanded."""
    found = set()
    for lo, hi in FR_RANGE.findall(text):
        found.update("FR-{:02d}".format(n) for n in range(int(lo), int(hi) + 1))
    found.update("FR-" + n for n in FR_ONE.findall(FR_RANGE.sub("", text)))
    return found


def code_map(files, root):
    """FR id -> files whose comments mention it."""
    out = {}
    for path in files:
        for fr in fr_ids(path.read_text(encoding="utf-8")):
            out.setdefault(fr, []).append(str(path.relative_to(root)))
    return out


def unit_tests():
    py = re.findall(r"^def test_fr(\d\d)_(\w+)\(", (A / "tests" / "test_rules.py").read_text(encoding="utf-8"), re.M)
    js = re.findall(r"^test\('FR-(\d\d) ([^']+)'", (B / "test" / "rules.test.js").read_text(encoding="utf-8"), re.M)
    py_names = ["FR-{} {}".format(n, words.replace("_", " ")) for n, words in py]
    js_names = ["FR-{} {}".format(n, words) for n, words in js]
    return py_names, js_names


def sanitize(text):
    """Keep machine-specific absolute paths out of the saved outputs."""
    text = re.sub(r"(pluggy-[\d.]+) -- \S+", r"\1", text)  # pytest -v prints the interpreter's full path
    for root, label in ((str(BUILD), "."), (str(BUILD.parent), ".."), (str(Path.home()), "~")):
        text = text.replace(root, label)
    return text


def run_suites(python):
    a = subprocess.run([python, "-m", "pytest", "-v", "-p", "no:cacheprovider"], cwd=A, capture_output=True, text=True)
    b = subprocess.run(["npm", "test", "--silent"], cwd=B, capture_output=True, text=True, shell=(os.name == "nt"))
    out_a, out_b = sanitize(a.stdout + a.stderr), sanitize(b.stdout + b.stderr)
    (BUILD / "docs" / "test-output-twin-a.txt").write_text("$ python -m pytest -v\n" + out_a, encoding="utf-8")
    (BUILD / "docs" / "test-output-twin-b.txt").write_text("$ npm test\n" + out_b, encoding="utf-8")
    passed_a = set(re.findall(r"::(test_\w+(?:\[[^\]]+\])?) PASSED", out_a))
    passed_b = set(re.findall(r"^\s*✔ (.+?) \(\d", out_b, re.M))
    return passed_a, passed_b, a.returncode, b.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="run both test suites and record the results")
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args()

    spec = json.loads((BUILD / "spec" / "requirements.json").read_text(encoding="utf-8"))
    scenarios = json.loads((BUILD / "spec" / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]
    map_a, map_b = code_map(A_CODE, A), code_map(B_CODE, B)
    py_names, js_names = unit_tests()
    paired = sorted(py_names) == sorted(js_names)

    results = None
    if args.run:
        python = os.path.abspath(args.python) if os.sep in args.python else args.python
        passed_a, passed_b, code_a, code_b = run_suites(python)
        results = {"a_exit": code_a, "b_exit": code_b, "a_passed": len(passed_a), "b_passed": len(passed_b)}

    rows = []
    for req in spec["requirements"]:
        fr = req["id"]
        units = [n for n in py_names if n.startswith(fr + " ")]
        scen = [s for s in scenarios if fr in s["fr"]]
        ok = None
        if results is not None:
            ok = all("test_fr{}_{}".format(fr[3:], n[6:].replace(" ", "_")) in passed_a for n in units)
            ok &= all(n in passed_b for n in units)
            ok &= all("test_scenario[{}_{}]".format(s["id"], "_".join(x.replace("-", "").lower() for x in s["fr"])) in passed_a for s in scen)
            ok &= all("{} {} {}".format(s["id"], " ".join(s["fr"]), s["title"]) in passed_b for s in scen)
        rows.append({"id": fr, "area": req["area"], "title": req["title"], "routes": req["routes"],
                     "twin_a_code": map_a.get(fr, []), "twin_b_code": map_b.get(fr, []),
                     "unit_tests": units, "scenarios": [s["id"] for s in scen], "passed_both": ok})

    (BUILD / "docs" / "traceability.json").write_text(json.dumps({"rows": rows, "unit_tests_paired": paired, "results": results}, indent=2) + "\n", encoding="utf-8")
    (BUILD / "docs" / "REQUIREMENTS.md").write_text(render(spec, rows, scenarios, paired, results), encoding="utf-8")
    missing = [r["id"] for r in rows if not r["twin_a_code"] or not r["twin_b_code"] or not (r["unit_tests"] or r["scenarios"])]
    print("requirements: {}   unit tests per suite: {}   paired: {}   scenarios: {}".format(len(rows), len(py_names), paired, len(scenarios)))
    if results:
        print("Twin A: {} passed (exit {})   Twin B: {} passed (exit {})".format(results["a_passed"], results["a_exit"], results["b_passed"], results["b_exit"]))
    if missing:
        print("requirements without code or tests:", ", ".join(missing))
    return 0 if paired and not missing and (results is None or all(r["passed_both"] for r in rows)) else 1


def render(spec, rows, scenarios, paired, results):
    L = []
    w = L.append
    w("# Expense Ledger: requirements and traceability")
    w("")
    w("_Generated by `tools/trace.py` from `spec/requirements.json`, `spec/scenarios.json`, the `FR-xx` comments in the code and the test names. Do not edit by hand._")
    w("")
    w(spec["summary"])
    w("")
    w("Both builds are judged by the same three things: the requirements below, the shared scenarios in `spec/scenarios.json` (run by both test suites) and `tools/parity_check.py`, which compares the two running builds byte for byte.")
    w("")
    w("| | Twin A | Twin B |")
    w("|---|---|---|")
    ta, tb = spec["stack"]["twin_a"], spec["stack"]["twin_b"]
    for label, key in (("Folder", "folder"), ("Language", "language"), ("Framework", "framework"), ("Templates", "templates"), ("Tests", "tests"), ("Port", "port"), ("Run", "run"), ("Test", "test")):
        a, b = ta[key], tb[key]
        if key in ("run", "test", "folder"):
            a, b = "`{}`".format(a), "`{}`".format(b)
        w("| {} | {} | {} |".format(label, a, b))
    w("")
    w(spec["stack"]["shared"])
    w("")
    w("## Requirements")
    w("")
    for req in spec["requirements"]:
        w("### {} {}: {}".format(req["id"], req["area"], req["title"]))
        w("")
        w("Routes: " + ", ".join("`{}`".format(r) for r in req["routes"]))
        w("")
        for b in req["behaviour"]:
            w("- " + b)
        w("")
    w("## Messages (identical wording in both builds)")
    w("")
    w("| Field | Rule | Message |")
    w("|---|---|---|")
    for m in spec["messages"]["validation"]:
        w("| {} | {} | {} |".format(m["field"], m["rule"], m["text"]))
    w("")
    w("| Notice key | Text shown after the redirect |")
    w("|---|---|")
    for n in spec["messages"]["notices"]:
        w("| `{}` | {} |".format(n["key"], n["text"]))
    w("")
    w("Categories, in their fixed order: " + ", ".join(c["label"] for c in spec["categories"]) + ".")
    w("")
    w("## Traceability matrix")
    w("")
    w("Each requirement, where it lives in each build, and the tests that prove it. Every unit test exists in both suites under the same name (" + ("paired one to one" if paired else "NOT PAIRED") + "); every scenario runs in both suites.")
    w("")
    w("| FR | Requirement | Twin A (Python/Flask) | Twin B (Node/Express) | Unit tests (each suite) | Scenarios | Both pass |")
    w("|---|---|---|---|---|---|---|")
    for r in rows:
        status = "not run" if r["passed_both"] is None else ("yes" if r["passed_both"] else "NO")
        w("| {} | {} | {} | {} | {} | {} | {} |".format(
            r["id"], r["title"], "<br>".join("`{}`".format(f) for f in r["twin_a_code"]), "<br>".join("`{}`".format(f) for f in r["twin_b_code"]),
            "<br>".join(n[6:] for n in r["unit_tests"]) or "–", ", ".join(r["scenarios"]) or "–", status))
    w("")
    w("## Scenarios (spec/scenarios.json)")
    w("")
    w("| ID | Proves | What it walks through | Steps |")
    w("|---|---|---|---|")
    for s in scenarios:
        w("| {} | {} | {} | {} |".format(s["id"], ", ".join(s["fr"]), s["title"], len(s["steps"])))
    w("")
    if results:
        w("Last run: Twin A {} tests passed (exit {}), Twin B {} tests passed (exit {}). Full output: `docs/test-output-twin-a.txt`, `docs/test-output-twin-b.txt`.".format(
            results["a_passed"], results["a_exit"], results["b_passed"], results["b_exit"]))
        w("")
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
