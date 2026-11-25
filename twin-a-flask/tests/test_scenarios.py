"""Runs the shared conformance fixture (tests/scenarios.json) against Twin A.

The same file is run by Twin B in test/scenarios.test.js, so both builds are
held to the same requests and the same expected responses. Each scenario is
tagged with the requirement IDs it proves (e.g. S11 -> FR-10).
"""

import json
from pathlib import Path

import pytest

FIXTURE = json.loads((Path(__file__).parent / "scenarios.json").read_text(encoding="utf-8"))
SCENARIOS = FIXTURE["scenarios"]


def _id(scenario):
    return "{}_{}".format(scenario["id"], "_".join(fr.replace("-", "").lower() for fr in scenario["fr"]))


def _send(client, step):
    method = step["method"]
    form = step.get("form")
    if method == "GET":
        return client.get(step["path"])
    return client.open(step["path"], method=method, data=form if form is not None else None)


def check(step, status, headers, body):
    """Assert one step's expectations. Same rules as check() in Twin B's test/helpers.js."""
    exp = step["expect"]
    where = "{} {}".format(step["method"], step["path"])
    assert status == exp["status"], where
    if "location" in exp:
        assert headers.get("Location") == exp["location"], where
    if "content_type" in exp:
        assert headers.get("Content-Type") == exp["content_type"], where
    if "disposition" in exp:
        assert headers.get("Content-Disposition") == exp["disposition"], where
    if exp.get("empty_body"):
        assert body == "", where
    if "body" in exp:
        assert body == exp["body"], where
    for text in exp.get("contains", []):
        assert text in body, "{}: missing {!r}".format(where, text)
    for text in exp.get("absent", []):
        assert text not in body, "{}: unexpected {!r}".format(where, text)
    pos = 0
    for text in exp.get("in_order", []):
        found = body.find(text, pos)
        assert found >= 0, "{}: {!r} missing or out of order".format(where, text)
        pos = found + len(text)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[_id(s) for s in SCENARIOS])
def test_scenario(client, scenario):
    assert FIXTURE["today"] == "2026-11-25"
    for step in scenario["steps"]:
        resp = _send(client, step)
        check(step, resp.status_code, resp.headers, resp.get_data(as_text=True))
