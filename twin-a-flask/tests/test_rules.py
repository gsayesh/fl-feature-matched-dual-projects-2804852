"""Unit tests for the rules behind the screens. Mirrors Twin B's test/rules.test.js.

Naming: test_fr<NN>_<what it proves>. Twin B has a test with the same words,
written "FR-NN what it proves", so tools/trace.py can pair them one to one.
"""

import json
from pathlib import Path

from ledger import dates, exports, queries
from ledger.config import MSG
from ledger.money import div_round, fmt, fmt_money, fmt_plain, fmt_signed, parse_amount
from ledger.store import Store
from ledger.text import encode, query
from ledger.validation import validate_expense

ROOT = Path(__file__).resolve().parent.parent
SEED = json.loads((ROOT / "seed.json").read_text(encoding="utf-8"))["expenses"]
TODAY = "2026-11-25"


def form(**kw):
    base = {"date": "2026-11-25", "description": "Test entry", "category": "other", "amount": "1.000", "notes": ""}
    base.update(kw)
    return base


# ------------------------------------------------------------------ FR-17 money and dates

def test_fr17_div_round_rounds_half_away_from_zero():
    assert div_round(5, 10) == 1      # 0.5 -> 1
    assert div_round(15, 10) == 2     # 1.5 -> 2
    assert div_round(25, 10) == 3     # 2.5 -> 3 (banker's rounding would give 2)
    assert div_round(4, 10) == 0
    assert div_round(-5, 10) == -1
    assert div_round(-15, 10) == -2
    assert div_round(14, 28) == 1
    assert div_round(10 ** 20 + 1, 2) == 5 * 10 ** 19 + 1  # stays exact far beyond 2**53


def test_fr17_amounts_format_with_three_decimals():
    assert fmt(1234500) == "1,234.500"
    assert fmt(0) == "0.000"
    assert fmt(-4150) == "−4.150"
    assert fmt_money(6200) == "OMR 6.200"
    assert fmt_signed(12300) == "+12.300"
    assert fmt_plain(-4150) == "-4.150"
    assert fmt_plain(1234500) == "1234.500"


def test_fr17_dates_use_iso_and_short_month_names():
    assert dates.date_long("2026-11-04") == "4 Nov 2026"
    assert dates.date_short("2026-11-04") == "4 Nov"
    assert dates.month_label(2026, 11) == "November 2026"
    assert dates.today_iso("2026-11-25") == "2026-11-25"


def test_fr17_leap_years_and_month_lengths():
    assert dates.days_in_month(2028, 2) == 29
    assert dates.days_in_month(2026, 2) == 28
    assert dates.is_leap(2000) and not dates.is_leap(2100)
    assert dates.parse_date("2026-02-29") is None
    assert dates.parse_date("2028-02-29") == (2028, 2, 29)
    assert dates.parse_date("1999-12-31") is None
    assert dates.parse_date("2026-1-05") is None
    assert dates.parse_date("2026-11-31") is None


def test_fr17_shift_month_wraps_years():
    assert dates.shift_month(2026, 1, -1) == (2025, 12)
    assert dates.shift_month(2026, 12, 1) == (2027, 1)
    assert dates.shift_month(2000, 1, -1) == (2000, 1)
    assert dates.shift_month(2099, 12, 1) == (2099, 12)


# ------------------------------------------------------------------ FR-10 validation

def test_fr10_amount_parsing_accepts_plain_numbers():
    assert parse_amount("12.5") == (12500, None)
    assert parse_amount("1,250.5") == (1250500, None)
    assert parse_amount("0.001") == (1, None)
    assert parse_amount("100000") == (100000000, None)
    assert parse_amount(" 7 ") == (7000, None)
    assert parse_amount("007.10") == (7100, None)


def test_fr10_amount_parsing_rejects_bad_input_in_rule_order():
    cases = {
        "": "amount_required",
        "abc": "amount_format",
        "1.2.3": "amount_format",
        "-5": "amount_format",
        "1e3": "amount_format",
        ".5": "amount_format",
        "5.": "amount_format",
        "١٢": "amount_format",  # Arabic-Indic digits are not accepted
        "1.2345": "amount_decimals",
        "0": "amount_zero",
        "0.000": "amount_zero",
        "100000.001": "amount_max",
        "9999999": "amount_max",
    }
    for raw, key in cases.items():
        assert parse_amount(raw) == (None, MSG[key]), raw


def test_fr10_text_limits_count_characters_not_bytes():
    assert validate_expense(form(description="ب" * 80))[1] == {}
    assert validate_expense(form(description="\U0001F600" * 80))[1] == {}  # emoji: 80 characters, 160 UTF-16 units
    assert validate_expense(form(description="ب" * 81))[1] == {"description": MSG["description_long"]}
    assert validate_expense(form(notes="n" * 200))[1] == {}
    assert validate_expense(form(notes="n" * 201))[1] == {"notes": MSG["notes_long"]}


def test_fr10_validation_trims_ascii_whitespace_only():
    values, errors, record = validate_expense(form(description="  Rent\t"))
    assert record["description"] == "Rent"
    values, errors, record = validate_expense(form(description="\u00a0Rent\u00a0"))  # no-break spaces are kept
    assert record["description"] == "\u00a0Rent\u00a0"
    values, errors, record = validate_expense(form(description="   "))
    assert errors == {"description": MSG["description_required"]}


# ------------------------------------------------------------------ FR-07 / FR-08 list rules

def test_fr07_search_ignores_case_and_matches_notes():
    found = queries.filter_rows(SEED, q="AL KHUWAIR")
    assert [r["id"] for r in found] == [1, 13, 24]
    assert len(queries.filter_rows(SEED, month="2026-11", category="utilities")) == 3


def test_fr07_query_strings_are_encoded_the_same_way():
    assert query([("q", "Al Khuwair & co"), ("month", "")]) == "?q=Al+Khuwair+%26+co"
    assert encode("أكتوبر") == "%D8%A3%D9%83%D8%AA%D9%88%D8%A8%D8%B1"
    assert query([]) == ""


def test_fr08_sort_ties_break_on_entry_number():
    rows = [
        {"id": 1, "date": "2026-11-01", "amount": 500},
        {"id": 2, "date": "2026-11-01", "amount": 500},
        {"id": 3, "date": "2026-10-01", "amount": 900},
    ]
    assert [r["id"] for r in queries.sort_rows(rows, "date_desc")] == [2, 1, 3]
    assert [r["id"] for r in queries.sort_rows(rows, "date_asc")] == [3, 1, 2]
    assert [r["id"] for r in queries.sort_rows(rows, "amount_desc")] == [3, 2, 1]
    assert [r["id"] for r in queries.sort_rows(rows, "amount_asc")] == [1, 2, 3]


# ------------------------------------------------------------------ FR-02..04, FR-13 figures

def test_fr02_month_summary_matches_hand_calculation():
    s = queries.month_summary(SEED, "2026-11", TODAY)
    assert (s["total"], s["count"], s["days"], s["average"]) == (496850, 13, 25, 19874)
    assert s["change"] == -65  # tenths of a percent: -6.5 %
    assert s["largest"]["id"] == 24
    assert [c["key"] for c in s["categories"]][:3] == ["housing", "groceries", "utilities"]


def test_fr04_axis_steps_are_1_2_or_5_times_a_power_of_ten():
    assert queries.nice_axis(531550) == (200000, 3)
    assert queries.nice_axis(4000) == (1000, 4)
    assert queries.nice_axis(9999) == (2000, 5)
    assert queries.nice_axis(1) == (1000, 1)
    assert queries.nice_axis(0) == (10000, 5)


def test_fr13_report_change_is_empty_without_previous_spending():
    rep = queries.report_rows(SEED, "2026-09")
    assert all(r["change_pct"] is None for r in rep["rows"])
    assert rep["rows"][0]["share"] == 546  # housing: 280.000 of 512.400 = 54.6 %
    assert rep["total"]["cur"] == 512400


# ------------------------------------------------------------------ FR-14 / FR-15 outputs

def test_fr14_csv_cells_guard_formulas_and_quote_specials():
    assert exports.cell("=1+1") == "'=1+1"
    assert exports.cell("-5") == "'-5"
    assert exports.cell("@home") == "'@home"
    assert exports.cell("a,b") == '"a,b"'
    assert exports.cell('say "hi"') == '"say ""hi"""'
    assert exports.cell("x\ny") == '"x\ny"'
    assert exports.cell("-4.150", text=False) == "-4.150"


def test_fr15_json_is_compact_with_stable_key_order():
    f = {"month": "all", "category": "all", "q": "", "sort": "date_desc"}
    body = exports.expenses_json(SEED[:1], f)
    assert body.startswith('{"currency":"OMR","filters":{"month":"all","category":"all","q":"","sort":"date_desc"},"count":1,')
    assert '"amount":"280.000","amount_minor":280000' in body


# ------------------------------------------------------------------ FR-17 storage

def test_fr17_store_creates_file_from_seed_and_never_reuses_ids(tmp_path):
    store = Store(tmp_path / "ledger.json", ROOT / "seed.json")
    assert len(store.expenses()) == 36
    record = {"date": "2026-11-25", "description": "x", "category": "other", "amount": 1000, "notes": ""}
    assert store.add(record) == 37
    assert store.delete(37) is True
    assert store.add(record) == 38
    store.clear()
    assert store.expenses() == []
    assert store.add(record) == 39
    store.reset()
    assert len(store.expenses()) == 36 and store.add(record) == 37


def test_fr17_store_file_format_is_stable(tmp_path):
    store = Store(tmp_path / "ledger.json", ROOT / "seed.json")
    store.add({"date": "2026-11-25", "description": "Karak", "category": "dining", "amount": 300, "notes": ""})
    text = (tmp_path / "ledger.json").read_text(encoding="utf-8")
    assert text.startswith('{\n  "version": 1,\n  "next_id": 38,\n  "expenses": [\n')
    assert '"id": 37,\n      "date": "2026-11-25",\n      "description": "Karak",' in text
    assert "فاتورة" in text  # Arabic kept as UTF-8, not \u escapes
    assert text.endswith("}\n")


# ------------------------------------------------------------------ FR-01 / FR-18 shell and errors

def test_fr01_every_screen_shares_the_shell(client):
    for path, section in [("/", "/"), ("/expenses", "/expenses"), ("/expenses/new", "/expenses/new"), ("/reports", "/reports"), ("/data", "/data")]:
        body = client.get(path).get_data(as_text=True)
        assert body.count('class="nav-link') == 5, path
        assert 'href="{}" aria-current="page">'.format(section) in body, path
        assert "Expense Ledger 1.0.0 · Amounts in Omani rial (OMR)" in body, path


def test_fr18_unknown_method_returns_405_page(client):
    resp = client.open("/reports", method="DELETE")
    assert resp.status_code == 405
    assert "<h1>Method not allowed</h1>" in resp.get_data(as_text=True)
