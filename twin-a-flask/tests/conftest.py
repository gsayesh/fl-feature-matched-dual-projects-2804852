"""Shared pytest fixtures for Twin A.

Every test gets its own temporary data file (created from seed.json on first
use) and a pinned "today" of 2026-11-25, so results never depend on the clock.
Twin B does the same in test/helpers.js.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so "import ledger" works without installing the package

from ledger import create_app  # noqa: E402

TODAY = "2026-11-25"


@pytest.fixture
def app(tmp_path):
    return create_app({"DATA_FILE": str(tmp_path / "ledger.json"), "TODAY": TODAY})


@pytest.fixture
def client(app):
    return app.test_client()
