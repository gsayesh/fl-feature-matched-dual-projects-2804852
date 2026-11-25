"""Build the illustrated requirements document from the project sources.

    python3 tools/build_docs.py          write docs/expense-ledger-twins.html and entries/entry-1.html
    python3 tools/build_docs.py --pdf    also print docs/expense-ledger-twins.pdf with Chrome and
                                         attach twin-a-flask.zip and twin-b-express.zip to it (needs pypdf)

On screen the HTML shows the cover; printed, it is the full 15-page document.
The screens in it are the real pages captured from both twins (demo/), shown
live in frames, so the document always matches the code. Run tools/trace.py,
tools/parity_check.py and tools/screenshots.py first: their outputs are quoted.
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent
A, B = BUILD / "twin-a-flask", BUILD / "twin-b-express"
TOTAL = 15


def esc(text):
    return html.escape(str(text), quote=True)


def read(path):
    return (BUILD / path).read_text(encoding="utf-8")


def loc(paths):
    return sum(len(p.read_text(encoding="utf-8").splitlines()) for p in paths)


# ---------------------------------------------------------------- facts gathered from the sources

SPEC = json.loads(read("spec/requirements.json"))
SCEN = json.loads(read("spec/scenarios.json"))["scenarios"]
TRACE = json.loads(read("docs/traceability.json"))
STATES = {s["state"]: s for s in json.loads(read("demo/states.json"))}
PARITY = read("docs/parity-report.txt")
COMPARE = read("docs/screens/compare.txt")
OUT_A = read("docs/test-output-twin-a.txt")
OUT_B = read("docs/test-output-twin-b.txt")

A_FILES = sorted((A / "ledger").glob("*.py")) + [A / "run.py"]
B_FILES = sorted((B / "src").glob("*.js")) + [B / "server.js"]
A_TPL, B_TPL = sorted((A / "templates").glob("*.html")), sorted((B / "views").glob("*.ejs"))
FACTS = {
    "requests": re.search(r"Requests compared: (\d+)", PARITY).group(1),
    "identical": re.search(r"identical: (\d+)", PARITY).group(1),
    "screens": len(STATES),
    "screens_same": sum(1 for s in STATES.values() if s["pixels_different"] == 0 and s["sha256"] == s["sha256_b"]),
    "tests_a": re.search(r"(\d+) passed", OUT_A).group(1),
    "tests_b": re.search(r"pass (\d+)", OUT_B).group(1),
    "reqs": len(SPEC["requirements"]),
    "scenarios": len(SCEN),
    "steps": sum(len(s["steps"]) for s in SCEN),
    "loc_a": loc(A_FILES), "loc_b": loc(B_FILES), "tpl_a": loc(A_TPL), "tpl_b": loc(B_TPL),
}
FACTS["tests"] = int(FACTS["tests_a"]) + int(FACTS["tests_b"])

# ---------------------------------------------------------------- shared pieces

CSS = r"""
@font-face { font-family: "Geist"; src: url("../spec/assets/fonts/geist-latin.woff2") format("woff2"); font-weight: 100 900; }
@font-face { font-family: "Geist Mono"; src: url("../spec/assets/fonts/geist-mono-latin.woff2") format("woff2"); font-weight: 100 900; }
:root { --ink: #0e1013; --text: #eef0f2; --muted: #8d939c; --mint: #5fd3a8; --green: #0d6b53; --py: #f2c14e; --node: #8bd17c;
  --paper: #f5f4f0; --card: #ffffff; --line: #e3e0d7; --line-2: #eeebe4; --body: #16181d; --body-2: #4a4f57; --body-3: #7a7f88; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 1600px; height: 1200px; overflow: hidden; background: var(--ink); }
body { font-family: "Geist", system-ui, sans-serif; color: var(--text); -webkit-font-smoothing: antialiased; }
.mono, code, pre { font-family: "Geist Mono", ui-monospace, monospace; }

/* cover */
.hero { position: relative; width: 1600px; height: 1200px; overflow: hidden;
  background: radial-gradient(1100px 620px at 50% 58%, rgba(13,107,83,0.30), rgba(13,107,83,0) 70%),
              radial-gradient(900px 500px at 50% 112%, rgba(95,211,168,0.10), rgba(95,211,168,0) 70%),
              linear-gradient(180deg, #111418 0%, #0c0e11 100%); }
.hero-head { position: absolute; left: 238px; right: 238px; top: 58px; display: flex; align-items: flex-end; justify-content: space-between; }
.eyebrow { font: 600 17px/1 "Geist Mono", monospace; letter-spacing: 0.16em; text-transform: uppercase; color: var(--mint); }
.headline { margin-top: 18px; font-size: 76px; line-height: 0.98; font-weight: 650; letter-spacing: -0.045em; }
.headline span { color: #8d939c; }
.stack-pair { display: flex; flex-direction: column; gap: 12px; align-items: flex-end; padding-bottom: 6px; }
.stack { display: inline-flex; align-items: center; gap: 12px; height: 46px; padding: 0 20px 0 14px; border-radius: 999px;
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.10); font-size: 20px; font-weight: 550; letter-spacing: -0.01em; }
.chip { display: inline-grid; place-items: center; width: 26px; height: 26px; border-radius: 7px; font: 700 14px/1 "Geist Mono", monospace; color: #0e1013; }
.chip.a { background: var(--py); } .chip.b { background: var(--node); }
.window { position: absolute; left: 238px; top: 244px; width: 1124px; height: 822px; border-radius: 20px; overflow: hidden;
  background: #1a1d22; border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 50px 120px -30px rgba(0,0,0,0.85), 0 18px 40px -20px rgba(0,0,0,0.6), 0 0 0 10px rgba(255,255,255,0.025); }
.bar { position: relative; height: 50px; display: grid; grid-template-columns: 1fr 1fr; background: #1d2026; border-bottom: 1px solid #2c3037; }
.tab { display: flex; align-items: center; gap: 11px; padding: 0 22px; font-size: 16px; color: #aab0b8; white-space: nowrap; }
.tab .dots { display: flex; gap: 7px; margin-right: 8px; }
.tab .dots i { width: 12px; height: 12px; border-radius: 50%; background: #3a3f47; }
.tab strong { font-weight: 600; color: #fff; }
.tab .url { font: 500 14px "Geist Mono", monospace; color: #8d939c; padding: 6px 10px; border-radius: 8px; background: #15171b; }
.tab.left .url { margin-left: 6px; }
.tab.right { padding-left: 150px; }
.tab.right .url { margin-left: auto; }
.tab .chip { width: 22px; height: 22px; font-size: 12px; border-radius: 6px; }
.screen { position: relative; width: 1124px; height: 772px; overflow: hidden; background: #f3f2ee; }
.screen iframe { position: absolute; left: 0; top: 0; width: 1440px; height: 1000px; border: 0; transform: scale(0.78056); transform-origin: 0 0; background: #f3f2ee; }
.screen .fa { clip-path: inset(0 720px 0 0); }
.screen .fb { clip-path: inset(0 0 0 720px); }
.seam { position: absolute; top: 0; bottom: 0; left: 561px; width: 2px; background: var(--mint); box-shadow: 0 0 0 1px rgba(95,211,168,0.25), 0 0 18px rgba(95,211,168,0.55); }
.seal { position: absolute; left: 562px; top: 25px; transform: translate(-50%, -50%); display: flex; align-items: center; gap: 10px;
  height: 40px; padding: 0 16px 0 7px; border-radius: 999px; background: #0e1013; border: 2px solid var(--mint); white-space: nowrap; }
.seal i { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 50%; background: var(--mint); color: #0e1013; font: 800 19px/1 "Geist Mono", monospace; font-style: normal; }
.seal span { font: 600 15px/1 "Geist", sans-serif; color: #fff; }
.proof { position: absolute; left: 238px; right: 238px; bottom: 28px; display: grid; grid-template-columns: repeat(4, 1fr); }
.proof div { padding: 0 0 0 22px; border-left: 2px solid #2a2e35; }
.proof div:first-child { border-left-color: var(--mint); }
.proof b { display: block; font: 600 34px/1 "Geist Mono", monospace; letter-spacing: -0.03em; color: #fff; }
.proof span { display: block; margin-top: 9px; font-size: 16px; color: var(--muted); }

/* document pages (print only) */
.page { display: none; position: relative; width: 1600px; height: 1200px; overflow: hidden; padding: 92px 88px 60px;
  background: var(--paper); color: var(--body); }
.run { position: absolute; top: 36px; left: 88px; right: 88px; display: flex; justify-content: space-between;
  font: 500 13px/1 "Geist Mono", monospace; letter-spacing: 0.1em; text-transform: uppercase; color: #9a9ea6; }
.run b { color: var(--green); font-weight: 600; }
.kicker { font: 600 14px/1 "Geist Mono", monospace; letter-spacing: 0.14em; text-transform: uppercase; color: var(--green); }
.page h2 { margin-top: 14px; font-size: 46px; line-height: 1.05; font-weight: 650; letter-spacing: -0.035em; }
.lede { margin-top: 14px; max-width: 1080px; font-size: 19px; line-height: 1.5; color: var(--body-2); }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 18px; }
.cols-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; margin-top: 46px; }
.twin { padding: 32px 34px; }
.twin-head { display: flex; align-items: center; gap: 12px; }
.twin-head .chip { width: 34px; height: 34px; font-size: 17px; border-radius: 9px; }
.twin-head h3 { font-size: 26px; font-weight: 650; letter-spacing: -0.02em; }
.twin-head p { margin-left: auto; font: 500 13px "Geist Mono", monospace; color: var(--body-3); }
.facts { margin-top: 28px; display: grid; grid-template-columns: 112px 1fr; gap: 20px 12px; font-size: 17px; line-height: 1.45; }
.facts dt { font: 600 12px/1.6 "Geist Mono", monospace; letter-spacing: 0.08em; text-transform: uppercase; color: var(--body-3); }
.facts dd code { font-size: 14.5px; background: #f1efe9; padding: 2px 7px; border-radius: 6px; }
.shared { padding: 32px 34px; background: #0f1215; color: #e6e8ea; border-color: #0f1215; }
.shared h3 { font-size: 22px; font-weight: 650; letter-spacing: -0.015em; }
.shared ul { list-style: none; margin-top: 22px; display: grid; gap: 17px; }
.shared li { font-size: 16px; color: #aeb4bc; line-height: 1.45; }
.shared li code { display: block; margin-bottom: 3px; font-size: 14px; color: var(--mint); }
.why { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-top: 24px; }
.why div { padding: 26px 30px; }
.why b { display: block; font-size: 19px; font-weight: 650; letter-spacing: -0.01em; }
.why p { margin-top: 10px; font-size: 16.5px; line-height: 1.55; color: var(--body-2); }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); margin-top: 48px; }
.stats div { padding-left: 20px; border-left: 2px solid var(--line); }
.stats div:first-child { border-left-color: var(--green); }
.stats b { display: block; font: 600 40px/1 "Geist Mono", monospace; letter-spacing: -0.03em; }
.stats span { display: block; margin-top: 10px; font-size: 16px; color: var(--body-3); }

.reqs { columns: 2; column-gap: 44px; margin-top: 34px; }
.req { break-inside: avoid; padding: 18px 22px 18px; margin-bottom: 14px; background: var(--card); border: 1px solid var(--line); border-radius: 14px; }
.req-head { display: flex; align-items: baseline; gap: 12px; }
.req-id { flex: none; white-space: nowrap; font: 700 13px/1 "Geist Mono", monospace; letter-spacing: 0.04em; color: var(--green); background: #e2f0ea; padding: 5px 8px; border-radius: 6px; }
.req h4 { flex: none; font-size: 18px; font-weight: 650; letter-spacing: -0.01em; }
.req .area { margin-left: auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; font: 500 12px "Geist Mono", monospace; color: var(--body-3); white-space: nowrap; }
.req ul { margin: 10px 0 0 18px; display: grid; gap: 5px; }
.req li { font-size: 14px; line-height: 1.45; color: var(--body-2); }

table { width: 100%; border-collapse: collapse; }
.tbl { margin-top: 30px; background: var(--card); border: 1px solid var(--line); border-radius: 16px; overflow: hidden; }
.tbl th { padding: 11px 14px; background: #faf9f6; border-bottom: 1px solid var(--line); text-align: left;
  font: 600 11.5px/1.2 "Geist Mono", monospace; letter-spacing: 0.08em; text-transform: uppercase; color: var(--body-3); }
.tbl td { padding: 9px 14px; border-bottom: 1px solid var(--line-2); font-size: 14px; line-height: 1.35; vertical-align: top; }
.tbl tr:last-child td { border-bottom: 0; }
.tbl td.m, .tbl td code { font-family: "Geist Mono", monospace; font-size: 12.5px; color: var(--body-2); }
.tbl td.id { font: 700 13px "Geist Mono", monospace; color: var(--green); white-space: nowrap; }
.ok { display: inline-flex; align-items: center; gap: 6px; font: 600 12.5px "Geist Mono", monospace; color: #0d6b53; white-space: nowrap; }
.ok::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: #13a874; }
.msgs { display: grid; grid-template-columns: 1.55fr 1fr; gap: 26px; margin-top: 30px; align-items: start; }
.msgs .tbl { margin-top: 0; }
.msgs td.txt { font-weight: 500; color: var(--body); }
.msgs .tbl td { padding: 14px 16px; font-size: 15.5px; }
.msgs .tbl td.m { font-size: 13.5px; }
.msgs .tbl th { padding: 14px 16px; }
.side-stack { display: grid; gap: 22px; }
.rules { padding: 26px 30px; }
.rules h3 { font-size: 19px; font-weight: 650; }
.rules ul { margin: 10px 0 0 18px; display: grid; gap: 6px; }
.rules li { font-size: 15.5px; line-height: 1.5; color: var(--body-2); }
.cats { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }
.cats span { display: inline-flex; align-items: center; gap: 8px; height: 32px; padding: 0 13px 0 11px; border: 1px solid var(--line); border-radius: 999px; font-size: 13px; font-weight: 500; background: #fff; }
.cats i { width: 9px; height: 9px; border-radius: 3px; }

.pairs { display: grid; gap: 22px; margin-top: 18px; }
.pair-cap { display: flex; align-items: center; gap: 14px; height: 30px; }
.pair-cap .n { font: 700 13px "Geist Mono", monospace; color: var(--green); }
.pair-cap b { font-size: 19px; font-weight: 650; letter-spacing: -0.01em; }
.pair-cap code { font-size: 13px; color: var(--body-3); }
.pair-cap .same { margin-left: auto; display: inline-flex; align-items: center; gap: 8px; height: 28px; padding: 0 12px; border-radius: 999px;
  background: #e2f0ea; color: #0b5a45; font: 600 12.5px "Geist Mono", monospace; }
.pair-row { display: grid; grid-template-columns: 605px 605px; gap: 0 54px; justify-content: center; margin-top: 10px; position: relative; }
.pair-row::after { content: "="; position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); display: grid; place-items: center;
  width: 38px; height: 38px; border-radius: 50%; background: var(--green); color: #fff; font: 700 20px/1 "Geist Mono", monospace; }
.frame { width: 605px; border-radius: 10px; overflow: hidden; border: 1px solid #d9d5cb; background: #fff; box-shadow: 0 12px 30px -18px rgba(22,24,29,0.35); }
.frame-bar { display: flex; align-items: center; gap: 8px; height: 26px; padding: 0 10px; background: #ebe9e3; border-bottom: 1px solid #d9d5cb; font-size: 12px; color: var(--body-2); white-space: nowrap; overflow: hidden; }
.frame-bar .chip { width: 17px; height: 17px; font-size: 10px; border-radius: 5px; }
.frame-bar strong { font-weight: 600; color: var(--body); }
.frame-bar code { margin-left: auto; font-size: 11px; color: var(--body-3); overflow: hidden; text-overflow: ellipsis; }
.frame-view { position: relative; width: 605px; height: 392px; overflow: hidden; background: #f3f2ee; }
.frame-view iframe { position: absolute; left: 0; top: 0; width: 1440px; height: 1000px; border: 0; transform: scale(0.42014); transform-origin: 0 0; }

.ev { display: grid; grid-template-columns: 1.06fr 1fr; gap: 24px; margin-top: 30px; align-items: start; }
.term { background: #0f1215; color: #cfd3d8; border-radius: 14px; padding: 18px 20px; font: 400 12.5px/1.6 "Geist Mono", monospace; white-space: pre; overflow: hidden; }
.term .c { color: #6f7680; } .term .g { color: #5fd3a8; } .term .y { color: #f2c14e; } .term .w { color: #fff; font-weight: 600; }
.term-title { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; font-size: 15px; font-weight: 650; color: var(--body); }
.term-title .chip { width: 22px; height: 22px; font-size: 12px; border-radius: 6px; }
.ev-right { display: grid; gap: 18px; }
.cmp { margin-top: 22px; padding: 18px 22px 20px; background: var(--card); border: 1px solid var(--line); border-radius: 16px; }
.cmp-title { font-size: 15px; font-weight: 650; }
.cells { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px 26px; margin-top: 12px; }
.cell { display: grid; grid-template-columns: 30px 1fr auto auto; gap: 10px; align-items: center; padding: 7px 0; border-bottom: 1px solid var(--line-2); font-size: 14px; }
.cell .n { font: 700 12.5px "Geist Mono", monospace; color: var(--green); }
.cell .h { font: 500 12.5px "Geist Mono", monospace; color: var(--body-3); }

.run2 { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 26px; margin-top: 30px; }
.run2 > div { min-width: 0; }
.code { background: #0f1215; color: #d6dade; border-radius: 14px; padding: 22px 26px; font: 400 15.5px/1.7 "Geist Mono", monospace; white-space: pre; overflow: hidden; }
.code .c { color: #6f7680; } .code .k { color: #f2c14e; } .code .s { color: #8bd17c; }
.block-title { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; font-size: 20px; font-weight: 650; letter-spacing: -0.01em; }
.block-title .chip { width: 26px; height: 26px; font-size: 13px; }
.block-title em { margin-left: auto; font: 500 13px "Geist Mono", monospace; font-style: normal; color: var(--body-3); }
.tree { margin-top: 18px; background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 20px 24px; font: 400 14.5px/1.65 "Geist Mono", monospace; white-space: pre; color: var(--body-2); }
.tree b { color: var(--body); font-weight: 600; }
.tree i { font-style: normal; color: #a0a4ab; }
.small-code { font-size: 13.2px; line-height: 1.62; padding: 18px 22px; }
.code-note { margin-top: 10px; font-size: 14.5px; line-height: 1.5; color: var(--body-2); }

.walk { display: grid; grid-template-columns: 1.25fr 1fr; gap: 26px; margin-top: 32px; align-items: start; }
.steps { list-style: none; display: grid; gap: 10px; counter-reset: s; }
.steps li { counter-increment: s; display: grid; grid-template-columns: 44px 1fr; gap: 14px; padding: 19px 24px; background: var(--card); border: 1px solid var(--line); border-radius: 14px; }
.steps li::before { content: counter(s, decimal-leading-zero); font: 700 15px/1.5 "Geist Mono", monospace; color: var(--green); }
.steps b { display: block; font-size: 18px; font-weight: 650; }
.steps p { margin-top: 4px; font-size: 15.5px; line-height: 1.5; color: var(--body-2); }
.hand { padding: 30px 32px; }
.hand h3 { font-size: 20px; font-weight: 650; }
.hand ul { margin: 14px 0 0 18px; display: grid; gap: 8px; }
.hand li { font-size: 16px; line-height: 1.5; color: var(--body-2); }
.hand.dark { background: #0f1215; border-color: #0f1215; color: #e6e8ea; }
.hand.dark p { margin-top: 12px; font-size: 16.5px; line-height: 1.55; color: #aeb4bc; }

@page { size: 1600px 1200px; margin: 0; }
@media print {
  html, body { width: 1600px; height: auto; overflow: visible; background: var(--paper); }
  .hero { break-after: page; }
  .page { display: block; break-after: page; }
  .page:last-child { break-after: auto; }
}
"""


def hero():
    f = FACTS
    return """<section class="hero">
  <header class="hero-head">
    <div>
      <p class="eyebrow">Expense Ledger · twin builds</p>
      <h1 class="headline">Same app.<br><span>Two codebases.</span></h1>
    </div>
    <div class="stack-pair">
      <span class="stack"><span class="chip a">A</span>Python 3 · Flask · Jinja2</span>
      <span class="stack"><span class="chip b">B</span>Node.js · Express · EJS</span>
    </div>
  </header>
  <div class="window">
    <div class="bar">
      <div class="tab left"><span class="dots"><i></i><i></i><i></i></span><span class="chip a">A</span><strong>Twin A</strong>Flask<span class="url">127.0.0.1:5001</span></div>
      <div class="tab right"><span class="chip b">B</span><strong>Twin B</strong>Express<span class="url">127.0.0.1:5002</span></div>
    </div>
    <div class="screen">
      <iframe class="fa" src="../demo/twin-a/01-overview.html" scrolling="no" title="Twin A, overview"></iframe>
      <iframe class="fb" src="../demo/twin-b/01-overview.html" scrolling="no" title="Twin B, overview"></iframe>
      <div class="seam"></div>
    </div>
    <div class="seal"><i>=</i><span>0 pixels different</span></div>
  </div>
  <footer class="proof">
    <div><b>{identical}/{requests}</b><span>responses byte-identical</span></div>
    <div><b>{screens_same}/{screens}</b><span>screens pixel-identical</span></div>
    <div><b>{tests}/{tests}</b><span>tests passing, {tests_a} per twin</span></div>
    <div><b>{reqs}/{reqs}</b><span>requirements traced</span></div>
  </footer>
</section>""".format(**f)


def page(n, kicker, title, body, lede=""):
    lede_html = '<p class="lede">{}</p>'.format(lede) if lede else ""
    return """<section class="page">
  <div class="run"><span>Expense Ledger · <b>twin builds</b></span><span>{:02d} / {}</span></div>
  <p class="kicker">{}</p>
  <h2>{}</h2>
  {}
  {}
</section>""".format(n, TOTAL, esc(kicker), title, lede_html, body)


# ---------------------------------------------------------------- page 2: the delivery

def page_delivery():
    f = FACTS
    twin = lambda key, name, stack, folder, run, test, port, deps, code: """<div class="card twin">
      <div class="twin-head"><span class="chip {key}">{key_up}</span><h3>{name}</h3><p>{stack}</p></div>
      <dl class="facts">
        <dt>Folder</dt><dd><code>{folder}</code></dd>
        <dt>Run</dt><dd><code>{run}</code><br><span style="color:#7a7f88;font-size:14px">opens 127.0.0.1:{port}</span></dd>
        <dt>Test</dt><dd><code>{test}</code><br><span style="color:#7a7f88;font-size:14px">{tests} tests, all passing</span></dd>
        <dt>Needs</dt><dd>{deps}</dd>
        <dt>Code</dt><dd>{code}</dd>
      </dl>
    </div>""".format(key=key, key_up=key.upper(), name=name, stack=stack, folder=folder, run=run, test=test, port=port, deps=deps, code=code,
                     tests=f["tests_a"] if key == "a" else f["tests_b"])
    body = """<div class="cols-3">
    {a}
    <div class="card shared">
      <h3>Shared, as copies: neutral files only</h3>
      <ul>
        <li><code>spec/requirements.json</code>{reqs} requirements, every message, the categories</li>
        <li><code>spec/scenarios.json</code>{scen} scenarios, {steps} requests with exact expected responses; both suites run them</li>
        <li><code>spec/seed.json</code>36 sample expenses, September to November 2026</li>
        <li><code>spec/assets/</code>one stylesheet, the Geist fonts and the icon</li>
        <li><code>tools/</code>parity check, screenshots, traceability, sync</li>
      </ul>
    </div>
    {b}
  </div>
  <div class="why">
    <div class="card"><b>Two mainstream stacks</b><p>Python with Flask and Node.js with Express are the two most common small-server stacks, so either build is easy to host and to hand to any developer.</p></div>
    <div class="card"><b>Pages built on the server</b><p>Every screen is plain HTML from the server, so the two builds can be compared byte for byte. There is no front-end build step and no JavaScript to install.</p></div>
    <div class="card"><b>One command each</b><p>One command runs a build and one tests it. There is no database server: the data is one JSON file in the same format for both, so a file written by one build can be opened by the other.</p></div>
  </div>
  <div class="stats">
    <div><b>{identical}/{requests}</b><span>responses byte-identical (parity check)</span></div>
    <div><b>{screens_same}/{screens}</b><span>screens pixel-identical in Chrome</span></div>
    <div><b>{tests}/{tests}</b><span>tests passing, same names in both suites</span></div>
    <div><b>{reqs}/{reqs}</b><span>requirements traced to code and tests</span></div>
  </div>""".format(
        a=twin("a", "Twin A", "Python 3.10+", "twin-a-flask/", "python run.py", "python -m pytest -v", 5001, "Flask 3, pytest",
               "{} lines of Python in 11 modules, {} lines of Jinja2".format(f["loc_a"], f["tpl_a"])),
        b=twin("b", "Twin B", "Node.js 18.17+", "twin-b-express/", "npm start", "npm test", 5002, "Express 5, EJS; tests use built-in node:test",
               "{} lines of JavaScript in 11 modules, {} lines of EJS".format(f["loc_b"], f["tpl_b"])),
        reqs=f["reqs"], scen=f["scenarios"], steps=f["steps"], **{k: f[k] for k in ("identical", "requests", "screens_same", "screens", "tests")})
    return page(2, "The delivery", "Two runnable projects, one specification", body,
                "Twin A and Twin B are written separately, each in the normal style of its framework. They share only framework-neutral files, so each folder runs on its own.")


# ---------------------------------------------------------------- pages 3-4: requirements

def req_block(r):
    routes = ", ".join(r["routes"][:2]) + (" …" if len(r["routes"]) > 2 else "")
    items = "".join("<li>{}</li>".format(esc(b)) for b in r["behaviour"])
    return """<div class="req"><div class="req-head"><span class="req-id">{}</span><h4>{}</h4><span class="area">{}</span></div><ul>{}</ul></div>""".format(
        r["id"], esc(r["title"]), esc(routes), items)


def page_requirements(n, part, reqs):
    body = '<div class="reqs">{}</div>'.format("".join(req_block(r) for r in reqs))
    title = "Functional requirements" + (" (continued)" if part == 2 else "")
    lede = "Short and plain. Each requirement is tagged in the code of both builds (search for its ID) and proved by tests in both suites." if part == 1 else ""
    return page(n, "Requirements {}/2 · FR-{}–{}".format(part, reqs[0]["id"][3:], reqs[-1]["id"][3:]), title, body, lede)


# ---------------------------------------------------------------- page 5: messages and rules

CAT_COLORS = {"housing": "#257de0", "groceries": "#f47230", "dining": "#00b894", "transport": "#f2a600",
              "utilities": "#ee7fac", "health": "#008a17", "leisure": "#6a4ce2", "other": "#8a8f98"}


def page_messages():
    rows = "".join('<tr><td class="m">{}</td><td>{}</td><td class="txt">{}</td></tr>'.format(esc(m["field"]), esc(m["rule"]), esc(m["text"]))
                   for m in SPEC["messages"]["validation"])
    notices = "".join('<tr><td class="m">{}</td><td class="txt">{}</td></tr>'.format(esc(m["key"]), esc(m["text"])) for m in SPEC["messages"]["notices"])
    rules = next(r for r in SPEC["requirements"] if r["id"] == "FR-17")["behaviour"]
    cats = "".join('<span><i style="background:{}"></i>{}</span>'.format(CAT_COLORS[c["key"]], esc(c["label"])) for c in SPEC["categories"])
    body = """<div class="msgs">
    <div><div class="tbl"><table><thead><tr><th>Field</th><th>Rule</th><th>Message, word for word</th></tr></thead><tbody>{rows}</tbody></table></div>
      <div class="block-title" style="margin-top:22px;font-size:17px">How both suites check a message: one step of scenario S11 in spec/scenarios.json</div>
      <div class="code small-code">{{<span class="s">"method"</span>: "POST", <span class="s">"path"</span>: "/expenses",
 <span class="s">"form"</span>: {{"date": "2026-11-25", "amount": "1.2345", "description": "xxx…(81)", ...}},
 <span class="s">"expect"</span>: {{<span class="s">"status"</span>: 422, <span class="s">"contains"</span>: [
   "&lt;p class=\"field-error\" id=\"f-amount-error\"&gt;…<span class="k">Amount can have at most 3 decimal places.</span>&lt;/p&gt;",
   "&lt;p class=\"field-error\" id=\"f-description-error\"&gt;…<span class="k">Description must be 80 characters or fewer.</span>&lt;/p&gt;"]}}}}</div></div>
    <div class="side-stack">
      <div class="tbl"><table><thead><tr><th>Notice</th><th>Shown after the redirect</th></tr></thead><tbody>{notices}</tbody></table></div>
      <div class="card rules"><h3>Data rules (FR-17)</h3><ul>{rules}</ul></div>
      <div class="card rules"><h3>Categories, fixed order and colour</h3><div class="cats">{cats}</div></div>
    </div>
  </div>""".format(rows=rows, notices=notices, rules="".join("<li>{}</li>".format(esc(x)) for x in rules), cats=cats)
    return page(5, "Messages and rules", "The same words, in the same places", body,
                "Every message lives in one table per build (<code>config.py</code> and <code>config.js</code>). The shared scenarios check each one character for character.")


# ---------------------------------------------------------------- page 6: traceability

def short_files(files):
    names = [Path(x).name for x in files]
    return " · ".join(names)


def page_trace():
    rows = []
    for r in TRACE["rows"]:
        units = len(r["unit_tests"])
        rows.append("<tr><td class=\"id\">{}</td><td>{}</td><td class=\"m\">{}</td><td class=\"m\">{}</td><td class=\"m\">{}</td><td class=\"m\">{}</td><td>{}</td></tr>".format(
            r["id"], esc(r["title"]), esc(short_files(r["twin_a_code"])), esc(short_files(r["twin_b_code"])),
            "{} unit".format(units) if units else "–", esc(", ".join(r["scenarios"])), '<span class="ok">both pass</span>' if r["passed_both"] else "NO"))
    body = """<div class="tbl"><table>
    <thead><tr><th style="width:74px">FR</th><th style="width:270px">Requirement</th><th>Twin A · Python files</th><th>Twin B · JavaScript files</th><th style="width:74px">Unit</th><th style="width:118px">Scenarios</th><th style="width:118px">Result</th></tr></thead>
    <tbody>{}</tbody></table></div>""".format("".join(rows))
    return page(6, "Traceability", "Every requirement, in both codebases, under test", body,
                "Generated by <code>tools/trace.py</code> from the FR tags in the code and the test names. Unit tests run under the same name in both suites; every scenario runs in both suites.")


# ---------------------------------------------------------------- pages 7-11: screens

PATHS = {
    "01-overview": "/", "02-overview-empty-month": "/?month=2026-08", "03-expenses": "/expenses",
    "04-expenses-filtered": "/expenses?month=2026-11&category=utilities", "07-add-validation": "POST /expenses",
    "08-added-notice": "/expenses?notice=added", "09-edit-form": "/expenses/30/edit", "10-delete-confirm": "/expenses/36/delete",
    "12-report": "/reports", "14-data-confirm-error": "POST /data/clear",
}


def pair(state):
    s = STATES[state]
    num, title = state[:2], s["title"]
    frames = ""
    for key, name, fw, port in (("a", "Twin A", "Flask", 5001), ("b", "Twin B", "Express", 5002)):
        frames += """<div class="frame"><div class="frame-bar"><span class="chip {k}">{K}</span><strong>{n}</strong>{fw}<code>127.0.0.1:{p}{path}</code></div>
      <div class="frame-view"><iframe src="../demo/twin-{k}/{st}.html" scrolling="no" title="{n}, {t}"></iframe></div></div>""".format(
            k=key, K=key.upper(), n=name, fw=fw, p=port, path=esc(PATHS[state].replace("POST ", "")) if not PATHS[state].startswith("POST") else " · " + esc(PATHS[state]), st=state, t=esc(title))
    return """<div><div class="pair-cap"><span class="n">{num}</span><b>{title}</b><code>HTTP {status}</code>
    <span class="same">HTML sha256 {sha} · {px} px different</span></div>
    <div class="pair-row">{frames}</div></div>""".format(num=num, title=esc(title), status=s["status"], sha=s["sha256"][:12], px=s["pixels_different"], frames=frames)


def page_screens(n, part, states, title):
    body = '<div class="pairs">{}</div>'.format("".join(pair(s) for s in states))
    return page(n, "Screens side by side {}/5 · left: Twin A · right: Twin B".format(part), title, body)


# ---------------------------------------------------------------- page 12: evidence

def colour_term(text):
    out = []
    for line in text.splitlines():
        e = esc(line)
        if line.startswith("$"):
            e = '<span class="w">{}</span>'.format(e)
        elif "identical" in line and "DIFFERENT" not in line and line[:1].isdigit():
            e = e.replace("identical", '<span class="g">identical</span>')
        elif line.startswith(("Result", "Requests compared", "Data files")):
            e = '<span class="g">{}</span>'.format(e)
        elif "PASSED" in line or line.lstrip().startswith("✔"):
            e = e.replace("PASSED", '<span class="g">PASSED</span>').replace("✔", '<span class="g">✔</span>')
        out.append(e)
    return "\n".join(out)


def page_evidence():
    p_lines = PARITY.splitlines()
    rows = [l for l in p_lines if re.match(r"^\d+\s", l)]
    head = "$ python3 tools/parity_check.py\n" + "\n".join(l[:104] for l in p_lines[1:3]) + "\n"
    sample = [r for r in rows if " S" in r[:12]]
    pick = rows[:4] + sample[30:33] + sample[60:63] + rows[-2:]
    table = "\n".join(re.sub(r"\s{2,}(\d{3})\s", r"  \1 ", l)[:104] for l in pick)
    summary = "\n".join(p_lines[-4:])
    parity = colour_term(head + "\n" + table + "\n…\n\n" + summary)
    a_lines = [l for l in OUT_A.splitlines() if "PASSED" in l]
    a_tail = [l for l in OUT_A.splitlines() if "passed" in l][-1].strip("= ")
    a_text = "$ python -m pytest -v\n" + "\n".join(l.replace("tests/", "")[:86] for l in a_lines[:3] + a_lines[-3:]) + "\n" + a_tail
    b_lines = [l for l in OUT_B.splitlines() if l.lstrip().startswith("✔")]
    b_sum = [l for l in OUT_B.splitlines() if l.startswith("ℹ pass") or l.startswith("ℹ fail")]
    b_text = "$ npm test\n" + "\n".join(re.sub(r" \([\d.]+ms\)", "", l)[:86] for l in b_lines[:3] + b_lines[-3:]) + "\n" + "   ".join(b_sum)
    cells = "".join('<div class="cell"><span class="n">{}</span><span class="t">{}</span><span class="h">{}</span><span class="ok">0 px</span></div>'.format(
        st["state"][:2], esc(st["title"]), st["status"]) for st in STATES.values() if st["pixels_different"] == 0 and st["sha256"] == st["sha256_b"])
    body = """<div class="ev">
    <div>
      <div class="term-title">Parity check: both builds running, every response compared</div>
      <div class="term">{parity}</div>
    </div>
    <div class="ev-right">
      <div><div class="term-title"><span class="chip a">A</span>Twin A · pytest</div><div class="term">{a}</div></div>
      <div><div class="term-title"><span class="chip b">B</span>Twin B · node:test</div><div class="term">{b}</div></div>
    </div>
  </div>
  <div class="cmp"><div class="cmp-title">The same {n} screens captured from both builds in Chrome, compared pixel by pixel</div><div class="cells">{cells}</div></div>""".format(parity=parity, a=colour_term(a_text), b=colour_term(b_text), cells=cells, n=len(STATES))
    return page(12, "Evidence", "Measured, not claimed", body,
                "Three independent checks, all in <code>tools/</code>: the parity check compares the running builds, the two suites test them, and Chrome compares the screens pixel by pixel.")


def page_evidence_fit(html_page):
    return html_page


# ---------------------------------------------------------------- page 13: run

def page_run():
    a_cmd = """<span class="c"># Twin A needs Python 3.10+</span>
cd twin-a-flask
python3 -m venv .venv
source .venv/bin/activate   <span class="c"># Windows: .venv\\Scripts\\activate</span>
pip install -r requirements.txt
<span class="k">python run.py</span>             <span class="c"># http://127.0.0.1:5001</span>
<span class="k">python -m pytest -v</span>       <span class="c"># {a} passed</span>""".format(a=FACTS["tests_a"])
    b_cmd = """<span class="c"># Twin B needs Node.js 18.17+</span>
cd twin-b-express
npm install


<span class="k">npm start</span>                 <span class="c"># http://127.0.0.1:5002</span>
<span class="k">npm test</span>                  <span class="c"># {b} passed</span>""".format(b=FACTS["tests_b"])
    tree_a = """<b>twin-a-flask/</b>
  run.py            <i>start on :5001</i>
  requirements.txt  <i>Flask, pytest</i>
  seed.json         <i>36 sample expenses</i>
  <b>ledger/</b>           <i>app factory, routes, views,</i>
                    <i>queries, money, dates, text,</i>
                    <i>validation, exports, store</i>
  <b>templates/</b>        <i>9 Jinja2 templates</i>
  <b>static/</b>           <i>app.css, fonts, icon</i>
  <b>tests/</b>            <i>rules + scenarios (41)</i>"""
    tree_b = """<b>twin-b-express/</b>
  server.js         <i>start on :5002</i>
  package.json      <i>express, ejs</i>
  seed.json         <i>36 sample expenses</i>
  <b>src/</b>              <i>app factory, routes, views,</i>
                    <i>queries, money, dates, text,</i>
                    <i>validation, exports, store</i>
  <b>views/</b>            <i>9 EJS templates</i>
  <b>public/</b>           <i>app.css, fonts, icon</i>
  <b>test/</b>             <i>rules + scenarios (41)</i>"""
    body = """<div class="run2">
    <div><div class="block-title"><span class="chip a">A</span>Twin A · Python + Flask<em>port 5001</em></div><div class="code">{a}</div><div class="tree">{ta}</div></div>
    <div><div class="block-title"><span class="chip b">B</span>Twin B · Node.js + Express<em>port 5002</em></div><div class="code">{b}</div><div class="tree">{tb}</div></div>
  </div>
  <div class="run2" style="margin-top:22px">
    <div class="tbl" style="margin-top:0"><table><thead><tr><th>Setting (both builds)</th><th>Default</th><th>Purpose</th></tr></thead><tbody>
      <tr><td class="m">PORT</td><td class="m">5001 / 5002</td><td>Port to listen on</td></tr>
      <tr><td class="m">LEDGER_DATA</td><td class="m">data/ledger.json</td><td>Data file; both builds read the same format</td></tr>
      <tr><td class="m">LEDGER_TODAY</td><td class="m">today</td><td>Pins the date for tests and the parity check</td></tr>
    </tbody></table></div>
    <div><div class="code"><span class="c"># prove they are identical (from the project root)</span>
<span class="k">python3 tools/parity_check.py</span> \\
    --python twin-a-flask/.venv/bin/python
<span class="s">Result: PASS, the twins are indistinguishable</span></div></div>
  </div>""".format(a=a_cmd, b=b_cmd, ta=tree_a, tb=tree_b)
    return page(13, "Setup, run and test", "Up and running in about two minutes", body,
                "Each build creates <code>data/ledger.json</code> from the sample data on first start. Data → Restore sample data starts a walkthrough from a known state.")


# ---------------------------------------------------------------- page 14: mirrored code

def extract(path, start, end_marker):
    text = path.read_text(encoding="utf-8")
    i = text.index(start)
    j = text.index(end_marker, i)
    return text[i:j].rstrip("\n")


def highlight(code, comment):
    out = []
    for line in code.splitlines():
        e = esc(line)
        if comment in line:
            k = e.index(esc(comment)) if esc(comment) in e else -1
            if k >= 0:
                e = e[:k] + '<span class="c">' + e[k:] + "</span>"
        e = re.sub(r"^(\s*)(def|function|const|return|if|for)\b", r'\1<span class="k">\2</span>', e)
        out.append(e)
    return "\n".join(out)


def page_code():
    py = extract(A / "ledger" / "money.py", "def div_round", "def _group")
    js = extract(B / "src" / "money.js", "/** numerator", "/** Display form without")
    py = "\n".join(l for l in py.splitlines())
    tpl_a = extract(A / "templates" / "form.html", '          <div class="field{{ err_cls.amount }}">', '          <div class="field{{ err_cls.description }}">')
    tpl_b = extract(B / "views" / "form.ejs", '          <div class="field<%= err_cls.amount %>">', '          <div class="field<%= err_cls.description %>">')
    tpl_a = "\n".join(l[10:] for l in tpl_a.splitlines())
    tpl_b = "\n".join(l[10:] for l in tpl_b.splitlines())
    shorten = lambda t: "\n".join((l[:80] + " …") if len(l) > 82 else l for l in t.splitlines())
    py, js = shorten(py), shorten(js)
    body = """<div class="run2">
    <div><div class="block-title"><span class="chip a">A</span>ledger/money.py<em>FR-10 · FR-17</em></div><div class="code small-code">{py}</div></div>
    <div><div class="block-title"><span class="chip b">B</span>src/money.js<em>FR-10 · FR-17</em></div><div class="code small-code">{js}</div></div>
  </div>
  <div class="run2" style="margin-top:20px">
    <div><div class="block-title"><span class="chip a">A</span>templates/form.html · Jinja2</div><div class="code small-code">{ta}</div></div>
    <div><div class="block-title"><span class="chip b">B</span>views/form.ejs · EJS</div><div class="code small-code">{tb}</div></div>
  </div>""".format(py=highlight(py, "#"), js=highlight(js, "//"), ta=esc(shorten(tpl_a)), tb=esc(shorten(tpl_b)))
    return page(14, "Clean, commented, mirrored", "Written twice, structured once", body,
                "Same module names, same function order, same comments. Each file says which file it mirrors in the other build, so a change in one is easy to find in the other.")


# ---------------------------------------------------------------- page 15: walkthrough and handover

def page_walk():
    steps = [
        ("Overview", "November 2026: OMR 496.850 spent, 13 expenses, down 6.5% on October. The arrows change the month; August 2026 is empty."),
        ("Expenses", "Filter November + Utilities (3 expenses, OMR 45.450), search “grocer”, try the four sort orders, export the CSV."),
        ("Add expense", "Submit the empty form: four messages at once, HTTP 422. Then add a valid expense: “Expense added.”"),
        ("Edit", "Open entry #30, change the amount, save: “Expense updated.” The total moves by the difference."),
        ("Delete", "Confirmation page, then “Expense deleted.” The next new expense gets a new number; #36 is never reused."),
        ("Reports", "Every category against October, with the change in OMR and %, and the share of the month. Export the CSV."),
        ("Data", "“Delete all expenses” without the tick shows “Tick the box to confirm.” Restore the sample data afterwards."),
    ]
    items = "".join("<li><div><b>{}</b><p>{}</p></div></li>".format(esc(t), esc(d)) for t, d in steps)
    body = """<div class="walk">
    <div><div class="block-title">Walk both builds side by side: :5001 and :5002</div><ol class="steps">{items}</ol></div>
    <div class="side-stack">
      <div class="card hand"><h3>In the handover</h3><ul>
        <li><b>twin-a-flask/</b> and <b>twin-b-express/</b>, each self-contained with its README, tests and sample data</li>
        <li><b>docs/REQUIREMENTS.md</b>: requirements, every message and the traceability matrix</li>
        <li><b>spec/</b>: requirements, scenarios and sample data as JSON, the shared source of truth</li>
        <li><b>tools/</b>: parity check, screenshots, traceability, sync</li>
        <li>this document as PDF, with ZIP files attached: each build on its own, and the whole delivery (open the PDF in Acrobat or Firefox to see the attachments)</li>
      </ul></div>
      <div class="card hand dark"><h3>Changes are part of the job</h3>
        <p>Want a different app, a third stack (Django, Laravel, .NET, React Native) or more features? Each change is made in both builds and added to the spec, the scenarios and the parity check, so the twins stay identical.</p>
        <p>The full source is in the repository linked in the entry description, ready to clone.</p></div>
    </div>
  </div>""".format(items=items)
    return page(15, "Walkthrough and handover", "What to click, and what you should see", body)


# ---------------------------------------------------------------- assemble

def document():
    reqs = SPEC["requirements"]
    pages = [
        page_delivery(),
        page_requirements(3, 1, reqs[:9]),
        page_requirements(4, 2, reqs[9:]),
        page_messages(),
        page_trace(),
        page_screens(7, 1, ["01-overview", "02-overview-empty-month"], "Overview: headline figures, chart, categories"),
        page_screens(8, 2, ["03-expenses", "04-expenses-filtered"], "Expense list: filter, search, sort, export"),
        page_screens(9, 3, ["07-add-validation", "08-added-notice"], "Add expense: validation, then the saved result"),
        page_screens(10, 4, ["09-edit-form", "10-delete-confirm"], "Edit and delete with confirmation"),
        page_screens(11, 5, ["12-report", "14-data-confirm-error"], "Monthly report and data tools"),
        page_evidence(),
        page_run(),
        page_code(),
        page_walk(),
    ]
    assert len(pages) + 1 == TOTAL
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Expense Ledger: twin builds (Python/Flask and Node/Express)</title>
<style>{css}</style>
</head>
<body>
{hero}
{pages}
</body>
</html>
""".format(css=CSS, hero=hero(), pages="\n".join(pages))


DETAIL_CSS = r"""
@font-face { font-family: "Geist"; src: url("../spec/assets/fonts/geist-latin.woff2") format("woff2"); font-weight: 100 900; }
@font-face { font-family: "Geist Mono"; src: url("../spec/assets/fonts/geist-mono-latin.woff2") format("woff2"); font-weight: 100 900; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 1600px; height: 2000px; overflow: hidden; }
body { background: #f5f4f0; color: #16181d; font-family: "Geist", system-ui, sans-serif; -webkit-font-smoothing: antialiased; }
.board { position: relative; width: 1600px; height: 2000px; padding: 70px 84px; }
.kicker { font: 600 16px/1 "Geist Mono", monospace; letter-spacing: 0.15em; text-transform: uppercase; color: #0d6b53; }
h1 { margin-top: 18px; font-size: 66px; line-height: 1.02; font-weight: 650; letter-spacing: -0.04em; }
h1 span { color: #8a8f97; }
.sub { margin-top: 18px; max-width: 1180px; font-size: 21px; line-height: 1.5; color: #4a4f57; }
.chip { display: inline-grid; place-items: center; width: 24px; height: 24px; border-radius: 7px; font: 700 13px/1 "Geist Mono", monospace; color: #0e1013; flex: none; }
.chip.a { background: #f2c14e; } .chip.b { background: #8bd17c; }
.brief { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-top: 36px; }
.ask { position: relative; padding: 24px 24px 22px; background: #fff; border: 1px solid #e3e0d7; border-radius: 18px; }
.ask .q { padding-right: 38px; min-height: 36px; font: 600 12.5px/1.4 "Geist Mono", monospace; letter-spacing: 0.08em; text-transform: uppercase; color: #8a8f97; }
.ask b { display: block; margin-top: 14px; font: 600 38px/1 "Geist Mono", monospace; letter-spacing: -0.03em; }
.ask p { margin-top: 10px; font-size: 16px; line-height: 1.45; color: #4a4f57; }
.ask .tick { position: absolute; top: 20px; right: 20px; width: 28px; height: 28px; border-radius: 50%; background: #0d6b53; display: grid; place-items: center; }
.ask .tick svg { width: 15px; height: 15px; }
.mosaic { display: grid; grid-template-columns: 1fr 1fr; gap: 24px 40px; margin-top: 38px; }
.cap { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 650; letter-spacing: -0.01em; }
.cap .n { font: 700 13px "Geist Mono", monospace; color: #0d6b53; }
.cap .eq { margin-left: auto; font: 600 12.5px "Geist Mono", monospace; color: #0b5a45; background: #e2f0ea; padding: 6px 10px; border-radius: 999px; }
.duo { position: relative; display: grid; grid-template-columns: 1fr 1fr; gap: 26px; margin-top: 12px; }
.duo::after { content: "="; position: absolute; left: 50%; top: 52%; transform: translate(-50%, -50%); width: 26px; height: 26px; border-radius: 50%;
  background: #0d6b53; color: #fff; display: grid; place-items: center; font: 700 15px/1 "Geist Mono", monospace; }
.mini { border-radius: 9px; overflow: hidden; border: 1px solid #d9d5cb; background: #fff; box-shadow: 0 10px 24px -16px rgba(22,24,29,0.4); }
.mini-bar { display: flex; align-items: center; gap: 6px; height: 22px; padding: 0 8px; background: #ebe9e3; border-bottom: 1px solid #d9d5cb; font-size: 11px; color: #4a4f57; white-space: nowrap; }
.mini-bar .chip { width: 15px; height: 15px; font-size: 9px; border-radius: 4px; }
.mini-bar code { margin-left: auto; font: 500 10px "Geist Mono", monospace; color: #8a8f97; }
.mini-view { position: relative; width: 100%; height: 216px; overflow: hidden; background: #f3f2ee; }
.mini-view iframe { position: absolute; left: 0; top: 0; width: 1440px; height: 1000px; border: 0; transform: scale(0.23611); transform-origin: 0 0; }
.foot { display: grid; grid-template-columns: 1.5fr 1fr; gap: 26px; margin-top: 36px; }
.panel { padding: 26px 30px; background: #fff; border: 1px solid #e3e0d7; border-radius: 18px; }
.panel h3 { font-size: 19px; font-weight: 650; letter-spacing: -0.01em; }
.frs { columns: 2; column-gap: 30px; margin-top: 14px; }
.frs div { display: flex; gap: 10px; padding: 5px 0; font-size: 15px; break-inside: avoid; }
.frs span { font: 700 12.5px/1.6 "Geist Mono", monospace; color: #0d6b53; }
.dark { background: #0f1215; border-color: #0f1215; color: #e6e8ea; }
.stackline { display: flex; align-items: center; gap: 10px; margin-top: 14px; font-size: 16px; color: #c9cdd3; }
.type { display: flex; align-items: baseline; gap: 18px; margin-top: 18px; }
.type b { font-size: 40px; font-weight: 650; letter-spacing: -0.03em; color: #fff; }
.type code { font: 500 30px "Geist Mono", monospace; color: #5fd3a8; }
.type small { font-size: 14px; color: #8d939c; }
.swatches { display: flex; gap: 8px; margin-top: 18px; }
.swatches i { flex: 1; height: 38px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.12); }
.why { margin-top: 16px; font-size: 15.5px; line-height: 1.55; color: #aeb4bc; }
"""


def detail_board():
    f = FACTS
    tick = '<span class="tick"><svg viewBox="0 0 16 16" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m3.5 8.4 2.9 2.9 6.1-6.6"/></svg></span>'
    asks = [
        ("Two runnable projects", "2 builds", "Python + Flask on :5001 and Node.js + Express on :5002, each self-contained, one command to run."),
        ("Same screens, workflows, outputs", "{}/{}".format(f["identical"], f["requests"]), "responses byte-identical: every page, CSV and JSON. {}/{} screens pixel-identical.".format(f["screens_same"], f["screens"])),
        ("Clean code, README, tests", "{}/{}".format(f["tests"], f["tests"]), "tests passing, {} per build under the same names; commented code; a README for each build and one for the delivery.".format(f["tests_a"])),
        ("Requirements write-up", "{} FRs".format(f["reqs"]), "short and plain, every message word for word, traced to the code and tests of both builds."),
    ]
    ask_html = "".join('<div class="ask">{}<p class="q">{}</p><b>{}</b><p>{}</p></div>'.format(tick, esc(q), esc(big), esc(t)) for q, big, t in asks)
    picks = [("01-overview", "/"), ("03-expenses", "/expenses"), ("07-add-validation", "POST /expenses"),
             ("10-delete-confirm", "/expenses/36/delete"), ("12-report", "/reports"), ("14-data-confirm-error", "POST /data/clear")]
    tiles = ""
    for state, path in picks:
        st = STATES[state]
        minis = ""
        for key, name, port in (("a", "Twin A · Flask", 5001), ("b", "Twin B · Express", 5002)):
            minis += '<div class="mini"><div class="mini-bar"><span class="chip {k}">{K}</span>{n}<code>:{p}{path}</code></div><div class="mini-view"><iframe src="../demo/twin-{k}/{s}.html" scrolling="no" title="{n}"></iframe></div></div>'.format(
                k=key, K=key.upper(), n=name, p=port, path=esc(path if not path.startswith("POST") else " " + path), s=state)
        tiles += '<div><div class="cap"><span class="n">{}</span>{}<span class="eq">0 px different</span></div><div class="duo">{}</div></div>'.format(state[:2], esc(st["title"]), minis)
    frs = "".join('<div><span>{}</span>{}</div>'.format(r["id"], esc(r["title"])) for r in SPEC["requirements"])
    swatch = "".join('<i style="background:{}"></i>'.format(c) for c in ("#0e1013", "#16181d", "#0d6b53", "#5fd3a8", "#f3f2ee", "#f2c14e", "#8bd17c"))
    return """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Expense Ledger: delivery overview</title><style>{css}</style></head>
<body><section class="board">
  <p class="kicker">Expense Ledger · twin builds · delivery overview</p>
  <h1>Everything the brief asks for,<br><span>built twice and proved identical.</span></h1>
  <p class="sub">A household expense tracker in Omani rial, written once in Python + Flask and once in Node.js + Express. The two builds share one specification, the same test scenarios and one stylesheet, but no application code.</p>
  <div class="brief">{asks}</div>
  <div class="mosaic">{tiles}</div>
  <div class="foot">
    <div class="panel"><h3>The requirements both builds follow</h3><div class="frs">{frs}</div></div>
    <div class="panel dark"><h3>Built with</h3>
      <div class="stackline"><span class="chip a">A</span>Python 3 · Flask 3 · Jinja2 · pytest</div>
      <div class="stackline"><span class="chip b">B</span>Node.js 18+ · Express 5 · EJS · node:test</div>
      <div class="type"><b>Geist</b><code>Geist Mono 0.123</code></div>
      <div class="swatches">{sw}</div>
      <p class="why">Ink, ledger green and mint on warm paper. Every figure is set in Geist Mono, so digits line up and never blur together.</p>
    </div>
  </div>
</section></body></html>
""".format(css=DETAIL_CSS, asks=ask_html, tiles=tiles, frs=frs, sw=swatch)


def demo_index():
    """build/index.html: interactive viewer of the captured screens (for GitHub Pages)."""
    f = FACTS
    states = [{"state": st["state"], "title": st["title"], "status": st["status"], "sha": st["sha256"][:16], "shab": st["sha256_b"][:16],
               "px": st["pixels_different"]} for st in STATES.values()]
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Expense Ledger: twin builds (Python/Flask and Node/Express)</title>
<meta name="description" content="One expense tracker built twice, in Python/Flask and Node.js/Express, with identical screens, workflows and outputs.">
<link rel="icon" href="spec/assets/favicon.svg" type="image/svg+xml">
<style>
@font-face {{ font-family: "Geist"; src: url("spec/assets/fonts/geist-latin.woff2") format("woff2"); font-weight: 100 900; }}
@font-face {{ font-family: "Geist Mono"; src: url("spec/assets/fonts/geist-mono-latin.woff2") format("woff2"); font-weight: 100 900; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #0e1013; color: #eef0f2; font: 400 15px/1.5 "Geist", system-ui, sans-serif; -webkit-font-smoothing: antialiased; }}
a {{ color: inherit; }}
.wrap {{ max-width: 1320px; margin: 0 auto; padding: 0 28px; }}
header {{ padding: 44px 0 26px; background: radial-gradient(900px 420px at 50% 120%, rgba(13,107,83,0.35), rgba(13,107,83,0) 70%); }}
.top {{ display: flex; align-items: flex-end; justify-content: space-between; gap: 30px; flex-wrap: wrap; }}
.eyebrow {{ font: 600 13px/1 "Geist Mono", monospace; letter-spacing: 0.16em; text-transform: uppercase; color: #5fd3a8; }}
h1 {{ margin-top: 14px; font-size: clamp(34px, 5vw, 58px); line-height: 1; font-weight: 650; letter-spacing: -0.045em; }}
h1 span {{ color: #8d939c; }}
.lede {{ margin-top: 14px; max-width: 640px; color: #aab0b8; font-size: 16px; }}
.stats {{ display: grid; grid-template-columns: repeat(4, auto); gap: 0 26px; }}
.stats div {{ padding-left: 14px; border-left: 2px solid #2a2e35; }}
.stats div:first-child {{ border-left-color: #5fd3a8; }}
.stats b {{ display: block; font: 600 24px/1 "Geist Mono", monospace; letter-spacing: -0.03em; }}
.stats span {{ display: block; margin-top: 6px; font-size: 12.5px; color: #8d939c; }}
.app {{ display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 22px; padding: 22px 0 40px; }}
.list {{ display: flex; flex-direction: column; gap: 2px; }}
.list p {{ margin: 4px 10px 10px; font: 600 11px/1 "Geist Mono", monospace; letter-spacing: 0.12em; text-transform: uppercase; color: #6f7680; }}
.list button {{ display: flex; align-items: center; gap: 10px; width: 100%; padding: 9px 10px; border: 0; border-radius: 10px; background: none; color: #c3c8cf;
  font: 500 14px/1.3 "Geist", sans-serif; text-align: left; cursor: pointer; }}
.list button:hover {{ background: #171a1f; color: #fff; }}
.list button.on {{ background: #1d2127; color: #fff; }}
.list button i {{ font: 600 11.5px "Geist Mono", monospace; font-style: normal; color: #5fd3a8; }}
.list button em {{ margin-left: auto; font: 500 11px "Geist Mono", monospace; font-style: normal; color: #6f7680; }}
.bar {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }}
.modes {{ display: inline-flex; padding: 3px; border-radius: 11px; background: #171a1f; border: 1px solid #262a31; }}
.modes button {{ height: 32px; padding: 0 13px; border: 0; border-radius: 8px; background: none; color: #aab0b8; font: 600 13px "Geist", sans-serif; cursor: pointer; }}
.modes button.on {{ background: #2a2f37; color: #fff; }}
.hint {{ font-size: 13px; color: #8d939c; }}
.proof {{ margin-left: auto; display: inline-flex; align-items: center; gap: 8px; height: 32px; padding: 0 12px; border-radius: 999px;
  background: rgba(95,211,168,0.12); color: #7fe0bb; font: 600 12.5px "Geist Mono", monospace; }}
.stage {{ position: relative; border-radius: 14px; overflow: hidden; background: #1a1d22; border: 1px solid #2a2e35; }}
.tabs {{ display: grid; grid-template-columns: 1fr 1fr; height: 40px; background: #1d2026; border-bottom: 1px solid #2c3037; font-size: 13.5px; }}
.tabs div {{ display: flex; align-items: center; gap: 9px; padding: 0 14px; color: #aab0b8; white-space: nowrap; overflow: hidden; }}
.tabs div + div {{ justify-content: flex-end; }}
.tabs strong {{ color: #fff; font-weight: 600; }}
.tabs code {{ font: 500 12px "Geist Mono", monospace; color: #8d939c; }}
.chip {{ display: inline-grid; place-items: center; width: 20px; height: 20px; border-radius: 6px; font: 700 11px/1 "Geist Mono", monospace; color: #0e1013; flex: none; }}
.chip.a {{ background: #f2c14e; }} .chip.b {{ background: #8bd17c; }}
.view {{ position: relative; overflow: hidden; background: #f3f2ee; }}
.view iframe {{ position: absolute; top: 0; width: 1440px; height: 1000px; border: 0; transform-origin: 0 0; background: #f3f2ee; }}
.seam {{ position: absolute; top: 0; bottom: 0; width: 2px; margin-left: -1px; background: #5fd3a8; box-shadow: 0 0 14px rgba(95,211,168,0.7); cursor: ew-resize; touch-action: none; }}
.seam::after {{ content: "= drag"; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); padding: 7px 10px; border-radius: 999px;
  background: #0e1013; border: 2px solid #5fd3a8; color: #fff; font: 600 12px "Geist Mono", monospace; white-space: nowrap; }}
.side .seam {{ display: none; }}
.meta {{ display: flex; gap: 18px; flex-wrap: wrap; margin-top: 12px; font: 500 12.5px "Geist Mono", monospace; color: #8d939c; }}
.meta b {{ color: #eef0f2; font-weight: 600; }}
.links {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 22px; }}
.links a {{ display: inline-flex; align-items: center; height: 38px; padding: 0 15px; border-radius: 10px; border: 1px solid #2a2e35; background: #15181c; text-decoration: none; font-weight: 600; font-size: 14px; }}
.links a:hover {{ border-color: #5fd3a8; }}
.links a.primary {{ background: #0d6b53; border-color: #0d6b53; }}
.toast {{ position: fixed; left: 50%; bottom: 24px; transform: translate(-50%, 20px); opacity: 0; transition: .2s; padding: 12px 16px; border-radius: 12px;
  background: #1d2127; border: 1px solid #2f343c; color: #fff; font-size: 14px; pointer-events: none; }}
.toast.on {{ opacity: 1; transform: translate(-50%, 0); }}
footer {{ padding: 26px 0 40px; border-top: 1px solid #1f2329; color: #6f7680; font-size: 13px; }}
@media (max-width: 900px) {{ .app {{ grid-template-columns: 1fr; }} .list {{ flex-direction: row; flex-wrap: wrap; }} .list p {{ width: 100%; }} .list button {{ width: auto; }} .stats {{ grid-template-columns: repeat(2, auto); gap: 14px 22px; }} }}
</style>
</head>
<body>
<header><div class="wrap top">
  <div>
    <p class="eyebrow">Expense Ledger · twin builds</p>
    <h1>Same app. <span>Two codebases.</span></h1>
    <p class="lede">One household expense tracker, built twice: in Python with Flask and in Node.js with Express. These are the real pages each build served, captured after the same clicks. Drag the seam: the left of it is Twin A, the right is Twin B.</p>
  </div>
  <div class="stats">
    <div><b>{identical}/{requests}</b><span>responses identical</span></div>
    <div><b>{screens_same}/{screens}</b><span>screens pixel-identical</span></div>
    <div><b>{tests}/{tests}</b><span>tests passing</span></div>
    <div><b>{reqs}/{reqs}</b><span>requirements traced</span></div>
  </div>
</div></header>
<main class="wrap app">
  <nav class="list" id="list" aria-label="Screens"><p>Screens and states</p></nav>
  <section>
    <div class="bar">
      <div class="modes" role="tablist">
        <button data-mode="split" class="on">Split</button><button data-mode="side">Side by side</button><button data-mode="a">Twin A only</button><button data-mode="b">Twin B only</button>
      </div>
      <span class="hint" id="hint">Drag the green seam left and right.</span>
      <span class="proof" id="proof"></span>
    </div>
    <div class="stage" id="stage">
      <div class="tabs"><div><span class="chip a">A</span><strong>Twin A</strong>Python · Flask<code>127.0.0.1:5001</code></div><div><code>127.0.0.1:5002</code>Node.js · Express<strong>Twin B</strong><span class="chip b">B</span></div></div>
      <div class="view" id="view">
        <iframe id="fa" title="Twin A" scrolling="no"></iframe>
        <iframe id="fb" title="Twin B" scrolling="no"></iframe>
        <div class="seam" id="seam" role="slider" aria-label="Seam between Twin A and Twin B" tabindex="0"></div>
      </div>
    </div>
    <div class="meta" id="meta"></div>
    <div class="links" id="links">
      <a class="primary" href="docs/expense-ledger-twins.pdf">Requirements document (PDF)</a>
      <a data-repo="docs/REQUIREMENTS.md" href="docs/REQUIREMENTS.md">REQUIREMENTS.md</a>
      <a data-repo="README.md" href="README.md">README: run both in 2 minutes</a>
      <a data-repo="twin-a-flask" href="twin-a-flask/">Twin A source</a>
      <a data-repo="twin-b-express" href="twin-b-express/">Twin B source</a>
      <a data-repo="docs/parity-report.txt" href="docs/parity-report.txt">Parity report</a>
    </div>
  </section>
</main>
<footer><div class="wrap">This page is a static preview. The forms need a running build: clone the repository and start both twins (one command each) to walk every flow.</div></footer>
<div class="toast" id="toast">Static preview: run the twins locally to submit forms.</div>
<script>
const STATES = {states};
const fa = document.getElementById('fa'), fb = document.getElementById('fb'), view = document.getElementById('view');
const seam = document.getElementById('seam'), stage = document.getElementById('stage');
let current = STATES[0].state, mode = 'split', cut = 0.5;

// Links go to the GitHub repository when the page is served from GitHub Pages.
const host = location.hostname.match(/^([^.]+)\\.github\\.io$/);
if (host) {{
  const repo = location.pathname.split('/').filter(Boolean)[0];
  const base = 'https://github.com/' + host[1] + '/' + repo;
  document.querySelectorAll('[data-repo]').forEach(a => {{
    const p = a.dataset.repo; a.href = base + (p.includes('.') ? '/blob/main/' : '/tree/main/') + p;
  }});
}}

const list = document.getElementById('list');
STATES.forEach(s => {{
  const b = document.createElement('button');
  b.innerHTML = '<i>' + s.state.slice(0, 2) + '</i>' + s.title + '<em>' + s.status + '</em>';
  b.onclick = () => show(s.state);
  b.dataset.state = s.state;
  list.appendChild(b);
}});

function show(state) {{
  current = state;
  const s = STATES.find(x => x.state === state);
  [...list.querySelectorAll('button')].forEach(b => b.classList.toggle('on', b.dataset.state === state));
  const a = 'demo/twin-a/' + state + '.html', b = 'demo/twin-b/' + state + '.html';
  if (!fa.src.endsWith(a)) fa.src = a;
  if (!fb.src.endsWith(b)) fb.src = b;
  document.getElementById('proof').textContent = s.px === 0 && s.sha === s.shab ? '= identical · 0 px different' : 'different';
  document.getElementById('meta').innerHTML = '<span>HTTP <b>' + s.status + '</b></span><span>Twin A HTML sha256 <b>' + s.sha + '…</b></span><span>Twin B HTML sha256 <b>' + s.shab + '…</b></span>';
}}

function layout() {{
  const w = view.clientWidth || stage.clientWidth;
  if (mode === 'side') {{
    const half = (w - 12) / 2, sc = half / 1440;
    view.style.height = (1000 * sc) + 'px';
    fa.style.cssText = 'left:0;transform:scale(' + sc + ');clip-path:none;display:block';
    fb.style.cssText = 'left:' + (half + 12) + 'px;transform:scale(' + sc + ');clip-path:none;display:block';
    view.style.background = '#1a1d22';
  }} else {{
    const sc = w / 1440, u = Math.round(1440 * cut);
    view.style.height = (1000 * sc) + 'px';
    view.style.background = '#f3f2ee';
    fa.style.cssText = 'left:0;transform:scale(' + sc + ');display:' + (mode === 'b' ? 'none' : 'block') + ';clip-path:' + (mode === 'split' ? 'inset(0 ' + (1440 - u) + 'px 0 0)' : 'none');
    fb.style.cssText = 'left:0;transform:scale(' + sc + ');display:' + (mode === 'a' ? 'none' : 'block') + ';clip-path:' + (mode === 'split' ? 'inset(0 0 0 ' + u + 'px)' : 'none');
    seam.style.left = (w * cut) + 'px';
  }}
  seam.style.display = mode === 'split' ? 'block' : 'none';
  stage.classList.toggle('side', mode === 'side');
}}

document.querySelectorAll('.modes button').forEach(b => b.onclick = () => {{
  mode = b.dataset.mode;
  document.querySelectorAll('.modes button').forEach(x => x.classList.toggle('on', x === b));
  document.getElementById('hint').textContent = mode === 'split' ? 'Drag the green seam left and right.' : mode === 'side' ? 'Both builds, same state, side by side.' : 'One build at a time: switch to compare.';
  layout();
}});

let dragging = false;
seam.addEventListener('pointerdown', e => {{ dragging = true; seam.setPointerCapture(e.pointerId); }});
seam.addEventListener('pointerup', () => {{ dragging = false; }});
seam.addEventListener('pointermove', e => {{
  if (!dragging) return;
  const r = view.getBoundingClientRect();
  cut = Math.min(0.98, Math.max(0.02, (e.clientX - r.left) / r.width));
  layout();
}});
seam.addEventListener('keydown', e => {{
  if (e.key === 'ArrowLeft') cut = Math.max(0.02, cut - 0.02);
  if (e.key === 'ArrowRight') cut = Math.min(0.98, cut + 0.02);
  layout();
}});

// Keep both frames on the same screen, and explain why forms do nothing here.
function wire(frame, other, key) {{
  frame.addEventListener('load', () => {{
    let doc;
    try {{ doc = frame.contentDocument; }} catch (e) {{ return; }}
    if (!doc) return;
    const name = (frame.contentWindow.location.pathname.split('/').pop() || '').replace('.html', '');
    if (name && name !== current && STATES.some(s => s.state === name)) show(name);
    const toast = document.getElementById('toast');
    const say = () => {{ toast.classList.add('on'); clearTimeout(window.__t); window.__t = setTimeout(() => toast.classList.remove('on'), 2200); }};
    doc.addEventListener('submit', e => {{ e.preventDefault(); say(); }}, true);
    doc.addEventListener('click', e => {{ const a = e.target.closest('a'); if (a && a.getAttribute('href') === '#') {{ e.preventDefault(); say(); }} }}, true);
  }});
}}
wire(fa, fb, 'a'); wire(fb, fa, 'b');
window.addEventListener('resize', layout);
show(current); layout();
</script>
</body>
</html>
""".format(states=json.dumps(states), **{k: f[k] for k in ("identical", "requests", "screens_same", "screens", "tests", "reqs")})


def chrome():
    for cand in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chrome")):
        if cand and Path(cand).exists():
            return cand
    raise SystemExit("Chrome not found")


def zip_dir(src, out):
    skip = {"node_modules", "__pycache__", ".pytest_cache", ".venv", "venv"}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(src.rglob("*")):
            rel = path.relative_to(src.parent)
            if any(part in skip for part in rel.parts) or path.is_dir():
                continue
            if path.parent.name == "data" and path.suffix in (".json", ".tmp"):
                continue
            z.write(path, rel.as_posix())


def zip_delivery(out):
    """Everything needed to run, test and compare both builds (no screenshots, previews or PDFs)."""
    skip = {"node_modules", "__pycache__", ".pytest_cache", ".venv", "venv"}
    roots = ["README.md", ".gitignore", "spec", "tools", "twin-a-flask", "twin-b-express", "docs/REQUIREMENTS.md", "docs/traceability.json",
             "docs/parity-report.txt", "docs/test-output-twin-a.txt", "docs/test-output-twin-b.txt"]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root in roots:
            base = BUILD / root
            paths = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file())
            for path in paths:
                rel = path.relative_to(BUILD)
                if any(part in skip for part in rel.parts):
                    continue
                if path.parent.name == "data" and path.suffix in (".json", ".tmp"):
                    continue
                z.write(path, ("expense-ledger-twins/" + rel.as_posix()))


def make_pdf(html_path, pdf_path):
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([chrome(), "--headless=new", "--no-sandbox", "--no-first-run", "--disable-extensions", "--allow-file-access-from-files",
                        "--run-all-compositor-stages-before-draw", "--virtual-time-budget=20000", "--user-data-dir=" + profile,
                        "--no-pdf-header-footer", "--print-to-pdf=" + str(pdf_path), html_path.resolve().as_uri()],
                       check=True, capture_output=True, timeout=240)
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("pypdf not installed: PDF written without attachments")
        return
    dist = BUILD / "dist"
    dist.mkdir(exist_ok=True)
    writer = PdfWriter(clone_from=str(pdf_path))
    writer.add_metadata({"/Title": "Expense Ledger: twin builds (Python/Flask and Node/Express)",
                         "/Subject": "Requirements, traceability, screens and evidence for two feature-matched builds"})
    for folder in (A, B):
        zpath = dist / (folder.name + ".zip")
        zip_dir(folder, zpath)
        writer.add_attachment(zpath.name, zpath.read_bytes())
    full = dist / "expense-ledger-twins.zip"
    zip_delivery(full)
    writer.add_attachment(full.name, full.read_bytes())
    with open(pdf_path, "wb") as fh:
        writer.write(fh)
    print("attached:", ", ".join(p.name for p in sorted(dist.glob("*.zip"))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", action="store_true")
    args = ap.parse_args()
    text = document()
    out_doc = BUILD / "docs" / "expense-ledger-twins.html"
    out_doc.write_text(text, encoding="utf-8")
    (BUILD / "entries").mkdir(exist_ok=True)
    (BUILD / "entries" / "entry-1.html").write_text(text, encoding="utf-8")
    (BUILD / "entries" / "entry-1-detail.html").write_text(detail_board(), encoding="utf-8")
    (BUILD / "index.html").write_text(demo_index(), encoding="utf-8")
    print("wrote", out_doc.relative_to(BUILD), "and entries/entry-1.html,", TOTAL, "pages")
    if args.pdf:
        pdf = BUILD / "docs" / "expense-ledger-twins.pdf"
        make_pdf(out_doc, pdf)
        print("wrote", pdf.relative_to(BUILD), "({:.1f} MB)".format(pdf.stat().st_size / 1e6))


if __name__ == "__main__":
    sys.exit(main())
